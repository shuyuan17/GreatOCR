from pathlib import Path
import subprocess
import sys

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr import cli


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "greatocr.cli", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def create_text_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, "Hello GreatOCR")
    pdf.save()


def test_doctor_outputs_python_and_greatocr_versions() -> None:
    result = run_cli("doctor")

    assert result.returncode == 0
    assert "Python:" in result.stdout
    assert "GreatOCR: 0.1.0" in result.stdout


def test_convert_accepts_existing_pdf_without_processing(tmp_path: Path) -> None:
    source_pdf = tmp_path / "sample.pdf"
    create_text_pdf(source_pdf)

    result = run_cli("convert", str(source_pdf))

    assert result.returncode == 0
    assert "Input validated" in result.stdout
    assert "conversion is not implemented in Phase 0" in result.stdout


def test_convert_rejects_non_pdf_file(tmp_path: Path) -> None:
    source_file = tmp_path / "sample.txt"
    source_file.write_text("not a pdf")

    result = run_cli("convert", str(source_file))

    assert result.returncode == 2
    assert "expected a .pdf file" in result.stderr


def test_convert_dry_run_prints_preflight_and_data_flow_summary(tmp_path: Path) -> None:
    source_pdf = tmp_path / "sample.pdf"
    create_text_pdf(source_pdf)

    result = run_cli("convert", str(source_pdf), "--dry-run")

    assert result.returncode == 0
    assert "Pages: 1" in result.stdout
    assert "native_text: 1" in result.stdout
    assert "Provider: not_configured" in result.stdout
    assert "Keep intermediates: yes" in result.stdout


def test_convert_show_progress_prints_text_progress(tmp_path: Path) -> None:
    source_pdf = tmp_path / "sample.pdf"
    create_text_pdf(source_pdf)

    result = run_cli("convert", str(source_pdf), "--dry-run", "--show-progress")

    assert result.returncode == 0
    assert "[##########----------] 50%" in result.stdout


def test_rework_pages_cli_calls_page_rework(monkeypatch, tmp_path: Path) -> None:
    calls = {}

    def fake_rework_pages(task_dir, pages, parser):
        calls["task_dir"] = task_dir
        calls["pages"] = pages

    monkeypatch.setattr(cli, "rework_pages", fake_rework_pages)

    assert cli.main(["rework", "--task-dir", str(tmp_path), "--pages", "5"]) == 0
    assert calls == {"task_dir": tmp_path, "pages": [5]}


def test_rework_tables_cli_calls_table_rework(monkeypatch, tmp_path: Path) -> None:
    calls = {}

    def fake_rework_tables(task_dir, table_ids, parser):
        calls["task_dir"] = task_dir
        calls["table_ids"] = table_ids

    monkeypatch.setattr(cli, "rework_tables", fake_rework_tables)

    assert (
        cli.main(["rework", "--task-dir", str(tmp_path), "--tables", "table-p0005-b0002"])
        == 0
    )
    assert calls == {"task_dir": tmp_path, "table_ids": ["table-p0005-b0002"]}
