from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from greatocr.paths import make_task_dir, safe_stem


def test_safe_stem_removes_unsafe_characters() -> None:
    assert safe_stem("../sample report:final?.pdf") == "sample_report_final"


def test_make_task_dir_uses_safe_name_timestamp_and_fingerprint(tmp_path: Path) -> None:
    source_pdf = tmp_path / "sample report.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    created_at = datetime(2026, 6, 25, 13, 45, 30, tzinfo=timezone.utc)

    task_dir = make_task_dir(tmp_path / "outputs", source_pdf, created_at)

    expected_fingerprint = sha256(source_pdf.read_bytes()).hexdigest()[:8]
    assert task_dir.name == f"sample_report_20260625-134530_{expected_fingerprint}"
    assert task_dir.is_dir()
