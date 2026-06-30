import json
from pathlib import Path

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.model.document import Document, Page
from greatocr.pipeline import run_pipeline
from greatocr.providers.fake import FakeDocumentParser
from greatocr.security import build_data_flow_summary
from greatocr.task.manifest import load_manifest


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


class FailingParser(FakeDocumentParser):
    def parse_document(self, source_pdf: Path, raw_result_dir: Path):
        raise AssertionError("parser should have been skipped")


def make_preflight(tmp_path: Path) -> PreflightResult:
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    return PreflightResult(
        source_path=source_pdf,
        file_sha256="a" * 64,
        encrypted=False,
        page_count=1,
        pages=[
            PagePreflight(
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
            )
        ],
    )


def make_summary(preflight: PreflightResult):
    return build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )


def test_parse_stage_success_updates_manifest(tmp_path: Path) -> None:
    preflight = make_preflight(tmp_path)

    run_pipeline(tmp_path / "task", preflight, FakeDocumentParser(FIXTURE), make_summary(preflight))

    manifest = load_manifest(tmp_path / "task" / "intermediates" / "task-manifest.json")
    assert manifest.stages["parse"].status == "succeeded"


def test_resume_from_document_json_after_docx_failure(tmp_path: Path) -> None:
    preflight = make_preflight(tmp_path)
    task_dir = tmp_path / "task"
    intermediates = task_dir / "intermediates"
    intermediates.mkdir(parents=True)
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
            )
        ],
    )
    (intermediates / "document.json").write_text(
        document.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (intermediates / "task-manifest.json").write_text(
        json.dumps(
            {
                "source_fingerprint": "a" * 64,
                "config": {},
                "stages": {
                    "parse": {"status": "succeeded"},
                    "model": {"status": "succeeded"},
                    "docx": {"status": "failed"},
                },
                "outputs": {},
            }
        ),
        encoding="utf-8",
    )

    run_pipeline(task_dir, preflight, FailingParser(FIXTURE), make_summary(preflight), resume=True)

    assert (task_dir / "result.docx").is_file()


def test_resume_does_not_repeat_succeeded_parse_stage(tmp_path: Path) -> None:
    preflight = make_preflight(tmp_path)
    task_dir = tmp_path / "task"
    run_pipeline(task_dir, preflight, FakeDocumentParser(FIXTURE), make_summary(preflight))

    run_pipeline(task_dir, preflight, FailingParser(FIXTURE), make_summary(preflight), resume=True)

    assert (task_dir / "quality-report.docx").is_file()
