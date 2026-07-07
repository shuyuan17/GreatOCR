from pathlib import Path
import subprocess
import sys

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import run_preflight
from greatocr.pipeline import run_pipeline, run_selected_page_groups
from greatocr.providers.fake import FakeDocumentParser
from greatocr.reasoning.base import CorrectionProposal, TextReasoner
from greatocr.security import SecurityMode, approve_data_flow, build_data_flow_summary
from greatocr.selection.page_ranges import parse_page_ranges
from greatocr.task.manifest import load_manifest
from greatocr.task.output_files import result_docx_name


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


class PipelineCountingReasoner(TextReasoner):
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def propose(self, document) -> list[CorrectionProposal]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("reasoner unavailable")
        return []


def create_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, "Acceptance sample")
    pdf.save()


def test_fake_provider_end_to_end_generates_required_outputs(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)
    preflight = run_preflight(pdf_path)
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )

    run_pipeline(tmp_path / "task", preflight, FakeDocumentParser(FIXTURE), summary)

    assert (tmp_path / "task" / result_docx_name(pdf_path.name)).is_file()
    assert (tmp_path / "task" / "quality-report.docx").is_file()
    assert (tmp_path / "task" / "intermediates" / "document.json").is_file()


def test_sensitive_mode_keeps_only_final_outputs(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)
    preflight = run_preflight(pdf_path)
    summary = build_data_flow_summary(
        EngineConfig(
            security_mode=SecurityMode.SENSITIVE,
            provider=ProviderConfig(name="fake", public=False, last_approved=True),
        ),
        preflight,
    )

    run_pipeline(tmp_path / "task", preflight, FakeDocumentParser(FIXTURE), summary)

    assert (tmp_path / "task" / result_docx_name(pdf_path.name)).is_file()
    assert (tmp_path / "task" / "quality-report.docx").is_file()
    assert not (tmp_path / "task" / "intermediates").exists()


def test_acceptance_script_runs_fake_provider() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_acceptance.py", "--provider", "fake"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "fake provider acceptance passed" in result.stdout


def test_selected_page_mapping_is_saved_and_restored_end_to_end(tmp_path: Path) -> None:
    pdf_path = tmp_path / "multi-page.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    for index in range(1, 4):
        pdf.drawString(72, 720, f"Page {index}")
        pdf.showPage()
    pdf.save()
    preflight = run_preflight(pdf_path)
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )

    document = run_pipeline(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
        selected_pages=[2],
    )
    manifest = load_manifest(tmp_path / "task" / "intermediates" / "task-manifest.json")

    assert manifest.config["selected_pages"] == [2]
    assert manifest.config["task_to_original"] == {"1": 2}
    assert document.pages[0].page_number == 2
    assert document.pages[0].task_page_number == 1


def test_reasoning_is_skipped_by_default_in_pipeline(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)
    preflight = run_preflight(pdf_path)
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )
    reasoner = PipelineCountingReasoner()

    run_pipeline(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
        reasoner=reasoner,
    )
    manifest = load_manifest(tmp_path / "task" / "intermediates" / "task-manifest.json")

    assert reasoner.calls == 0
    assert manifest.stages["reasoning"].status == "skipped"


def test_reasoner_failure_does_not_block_docx_generation(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)
    preflight = run_preflight(pdf_path)
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )
    reasoner = PipelineCountingReasoner(fail=True)

    document = run_pipeline(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
        reasoner=reasoner,
        reasoning_enabled=True,
    )

    assert (tmp_path / "task" / result_docx_name(pdf_path.name)).is_file()
    assert reasoner.calls == 1
    assert "reasoning_failed" in {issue.issue_type for issue in document.issues}


def test_pipeline_manifest_keeps_task_level_provider_approval(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)
    preflight = run_preflight(pdf_path)
    summary = approve_data_flow(
        build_data_flow_summary(
            EngineConfig(provider=ProviderConfig(name="fake", public=False)),
            preflight,
        ),
        ["fake-default", "private-backup"],
    )

    run_pipeline(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
    )
    manifest = load_manifest(tmp_path / "task" / "intermediates" / "task-manifest.json")

    assert manifest.approved_profile_ids == ["fake-default", "private-backup"]
    assert manifest.security_confirmation_at == summary.confirmed_at


def test_selected_ranges_can_generate_separate_named_outputs(tmp_path: Path) -> None:
    pdf_path = tmp_path / "multi-page.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    for index in range(1, 4):
        pdf.drawString(72, 720, f"Page {index}")
        pdf.showPage()
    pdf.save()
    preflight = run_preflight(pdf_path)
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )

    documents = run_selected_page_groups(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
        parse_page_ranges("1, 3", page_count=3),
        split_by_group=True,
    )

    assert [document.pages[0].page_number for document in documents] == [1, 3]
    assert (tmp_path / "task" / "result-pages-1.docx").is_file()
    assert (tmp_path / "task" / "result-pages-3.docx").is_file()
