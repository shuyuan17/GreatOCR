from pathlib import Path
from zipfile import ZipFile

from greatocr.model.document import Block, Document, Page, TextSpan
from greatocr.providers.mineru import MinerUConfig, ProviderConfigurationError
from greatocr.reports.quality_docx import write_quality_docx
from greatocr.validation.quality import compute_quality_summary


def test_task_outputs_do_not_contain_secret_value(tmp_path: Path) -> None:
    secret = "secret-value-12345"
    task_dir = tmp_path / "task"
    intermediates = task_dir / "intermediates"
    intermediates.mkdir(parents=True)
    (intermediates / "task-manifest.json").write_text('{"api_key":"***"}', encoding="utf-8")
    (intermediates / "quality-report.json").write_text('{"provider":"fake"}', encoding="utf-8")

    combined = "\n".join(path.read_text(encoding="utf-8") for path in task_dir.rglob("*.json"))

    assert secret not in combined


def test_provider_configuration_error_does_not_contain_secret() -> None:
    try:
        MinerUConfig.from_env({"MINERU_API_KEY": "secret-value-12345"})
    except ProviderConfigurationError as exc:
        assert "secret-value-12345" not in str(exc)


def test_quality_report_does_not_include_full_long_body_text(tmp_path: Path) -> None:
    long_text = "Confidential paragraph " * 20
    document = Document(
        document_id="doc-1",
        source_file_name="sample.pdf",
        file_sha256="a" * 64,
        page_count=1,
        provider_name="fake",
        pages=[
            Page(
                page_id="page-0001",
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
                blocks=[
                    Block(
                        block_id="block-1",
                        block_type="paragraph",
                        reading_order=1,
                        spans=[
                            TextSpan(
                                span_id="span-1",
                                original_text=long_text,
                                current_text=long_text,
                            )
                        ],
                    )
                ],
            )
        ],
    )
    summary = compute_quality_summary(document, [])
    report = write_quality_docx(summary, [], tmp_path / "quality-report.docx")

    xml_text = ZipFile(report).read("word/document.xml").decode("utf-8")

    assert long_text not in xml_text
