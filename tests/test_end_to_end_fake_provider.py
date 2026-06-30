from pathlib import Path
import subprocess
import sys

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import run_preflight
from greatocr.pipeline import run_pipeline
from greatocr.providers.fake import FakeDocumentParser
from greatocr.security import SecurityMode, build_data_flow_summary


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


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

    assert (tmp_path / "task" / "result.docx").is_file()
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

    assert (tmp_path / "task" / "result.docx").is_file()
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
