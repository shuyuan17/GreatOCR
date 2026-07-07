from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr.app.db import TaskDatabase
from greatocr.app.schemas import NewTask
from greatocr.app.services.credentials import CredentialService
from greatocr.app.services.task_processor import TaskProcessor
from greatocr.task.manifest import load_manifest
from tests.app.test_credentials import FakeKeyring


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


def create_pdf(path: Path) -> Path:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, "Acceptance sample")
    pdf.save()
    return path


def docx_text(path: Path) -> str:
    document = DocxDocument(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def save_provider(
    database: TaskDatabase,
    *,
    profile_id: str,
    display_name: str,
    adapter_type: str,
    endpoint: str,
    model: str | None = None,
    sensitive_allowed: bool = True,
) -> None:
    database.save_provider(
        {
            "profile_id": profile_id,
            "display_name": display_name,
            "adapter_type": adapter_type,
            "endpoint": endpoint,
            "model": model,
            "public": True,
            "sensitive_allowed": sensitive_allowed,
            "capabilities": {
                "native_pdf": True,
                "scanned_pdf": True,
                "coordinates": True,
                "layout": True,
                "tables": True,
                "images": True,
                "formulas": False,
                "languages": ["auto", "en", "zh"],
                "data_residency": "test",
                "translation": True,
                "text_processing": True,
            },
        }
    )


def make_processor(
    tmp_path: Path,
    *,
    translator_factory,
) -> tuple[TaskDatabase, CredentialService, TaskProcessor]:
    database = TaskDatabase(tmp_path / "greatocr.db")
    credentials = CredentialService(FakeKeyring())
    credentials.set("ocr-fake", "ocr-secret")
    credentials.set("zhipu-glm-default", "glm-secret")
    save_provider(
        database,
        profile_id="ocr-fake",
        display_name="Fake OCR",
        adapter_type="fake",
        endpoint=str(FIXTURE),
    )
    save_provider(
        database,
        profile_id="zhipu-glm-default",
        display_name="Zhipu GLM",
        adapter_type="openai-compatible",
        endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        model="glm-4-plus",
    )
    processor = TaskProcessor(
        database,
        credentials,
        translator_factory=translator_factory,
    )
    return database, credentials, processor


def test_ocr_only_does_not_create_translation_client_and_keeps_only_result_docx(
    tmp_path: Path,
) -> None:
    translation_calls: list[dict[str, str]] = []

    def translator_factory(**kwargs):
        translation_calls.append(kwargs)
        raise AssertionError("translator factory should not be called for OCR-only tasks")

    database, _, processor = make_processor(
        tmp_path,
        translator_factory=translator_factory,
    )
    try:
        source = create_pdf(tmp_path / "ocr-only.pdf")
        task = database.create_task(
            NewTask(
                source_path=str(source),
                pages=[1],
                provider_profile_id="ocr-fake",
                ocr_provider_profile_id="ocr-fake",
                processing_mode="ocr",
            )
        )

        status = processor.process(task)

        task_dir = Path(task.output_dir)
        assert status == "succeeded"
        assert translation_calls == []
        assert (task_dir / "ocr-only.docx").is_file()
        assert not (task_dir / "ocr-only_翻译.docx").exists()
    finally:
        database.close()


def test_translation_success_uses_generic_translator_and_preserves_original_result(
    tmp_path: Path,
) -> None:
    translation_calls: list[dict[str, str]] = []

    class Translator:
        def translate_texts(self, texts: list[str]) -> list[str]:
            return [f"ZH::{text}" if text else text for text in texts]

    def translator_factory(**kwargs):
        translation_calls.append(kwargs)
        return Translator()

    database, _, processor = make_processor(
        tmp_path,
        translator_factory=translator_factory,
    )
    try:
        source = create_pdf(tmp_path / "translation-success.pdf")
        task = database.create_task(
            NewTask(
                source_path=str(source),
                pages=[1],
                provider_profile_id="ocr-fake",
                ocr_provider_profile_id="ocr-fake",
                processing_mode="translation",
                translation_provider_profile_id="zhipu-glm-default",
                target_language="Chinese",
                translation_mode="page",
            )
        )

        status = processor.process(task)

        task_dir = Path(task.output_dir)
        result_text = docx_text(task_dir / "translation-success.docx")
        translated_text = docx_text(task_dir / "translation-success_翻译.docx")

        assert status == "succeeded"
        assert translation_calls == [
            {
                "api_key": "glm-secret",
                "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model_name": "glm-4-plus",
                "target_language": "中文",
                "provider_name": "Zhipu GLM",
            }
        ]
        assert "Sample Contract" in result_text
        assert "ZH::Sample Contract" in translated_text
        assert "ZH::" not in result_text
    finally:
        database.close()


def test_translation_failure_keeps_result_docx_and_returns_partial_without_fake_output(
    tmp_path: Path,
) -> None:
    class ExplodingTranslator:
        def translate_texts(self, texts: list[str]) -> list[str]:
            raise RuntimeError("Client error '401 Unauthorized' for url 'https://example.test'")

    def translator_factory(**kwargs):
        return ExplodingTranslator()

    database, _, processor = make_processor(
        tmp_path,
        translator_factory=translator_factory,
    )
    try:
        source = create_pdf(tmp_path / "translation-failure.pdf")
        task = database.create_task(
            NewTask(
                source_path=str(source),
                pages=[1],
                provider_profile_id="ocr-fake",
                ocr_provider_profile_id="ocr-fake",
                processing_mode="translation",
                translation_provider_profile_id="zhipu-glm-default",
                target_language="Chinese",
                translation_mode="page",
            )
        )

        status = processor.process(task)

        task_dir = Path(task.output_dir)
        manifest = load_manifest(task_dir / "intermediates" / "task-manifest.json")
        assert status == "partial"
        assert (task_dir / "translation-failure.docx").is_file()
        assert not (task_dir / "translation-failure_翻译.docx").exists()
        assert manifest.stages["translation"].status == "failed"
        assert (
            manifest.stages["translation"].message
            == "Translation Provider authentication failed. Please check API Key configuration."
        )
    finally:
        database.close()
