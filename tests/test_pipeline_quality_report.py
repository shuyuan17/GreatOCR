from pathlib import Path

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.model.document import Document, Page
from greatocr.pipeline import run_quality_stage
from greatocr.security import SecurityMode, build_data_flow_summary


def make_preflight() -> PreflightResult:
    return PreflightResult(
        source_path=Path("sample.pdf"),
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


def make_document() -> Document:
    return Document(
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


def test_quality_stage_writes_quality_report_docx(tmp_path: Path) -> None:
    preflight = make_preflight()
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )

    run_quality_stage(tmp_path / "task", make_document(), preflight, summary)

    assert (tmp_path / "task" / "quality-report.docx").is_file()


def test_normal_mode_keeps_quality_report_json(tmp_path: Path) -> None:
    preflight = make_preflight()
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )

    run_quality_stage(tmp_path / "task", make_document(), preflight, summary)

    assert (tmp_path / "task" / "intermediates" / "quality-report.json").is_file()


def test_sensitive_mode_does_not_keep_quality_report_json(tmp_path: Path) -> None:
    preflight = make_preflight()
    summary = build_data_flow_summary(
        EngineConfig(
            security_mode=SecurityMode.SENSITIVE,
            provider=ProviderConfig(name="fake", public=False, last_approved=True),
        ),
        preflight,
    )

    run_quality_stage(tmp_path / "task", make_document(), preflight, summary)

    assert not (tmp_path / "task" / "intermediates" / "quality-report.json").exists()
