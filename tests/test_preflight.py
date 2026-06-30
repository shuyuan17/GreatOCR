from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr.ingest.preflight import (
    InputFileNotFound,
    InvalidPdfError,
    run_preflight,
)


def create_text_pdf(path: Path, text: str = "Hello GreatOCR") -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, text)
    pdf.save()


def create_image_pdf(path: Path, text: str | None = None) -> None:
    image_path = path.with_suffix(".png")
    Image.new("RGB", (16, 16), color="black").save(image_path)

    pdf = canvas.Canvas(str(path), pagesize=letter)
    if text:
        pdf.drawString(72, 720, text)
    pdf.drawImage(str(image_path), 72, 640, width=48, height=48)
    pdf.save()


def create_encrypted_pdf(path: Path) -> None:
    plain_pdf = path.with_name("plain.pdf")
    create_text_pdf(plain_pdf)
    reader = PdfReader(str(plain_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("secret")
    with path.open("wb") as file:
        writer.write(file)


def test_run_preflight_returns_page_count_hash_and_encryption_flag(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    create_text_pdf(pdf_path)

    result = run_preflight(pdf_path)

    assert result.page_count == 1
    assert len(result.file_sha256) == 64
    assert result.encrypted is False
    assert result.pages[0].page_number == 1
    assert result.pages[0].width > 0
    assert result.pages[0].height > 0


def test_run_preflight_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputFileNotFound, match="does not exist"):
        run_preflight(tmp_path / "missing.pdf")


def test_run_preflight_raises_for_non_pdf(tmp_path: Path) -> None:
    text_file = tmp_path / "sample.txt"
    text_file.write_text("not a pdf")

    with pytest.raises(InvalidPdfError, match="expected a .pdf file"):
        run_preflight(text_file)


def test_run_preflight_detects_encrypted_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "encrypted.pdf"
    create_encrypted_pdf(pdf_path)

    result = run_preflight(pdf_path)

    assert result.encrypted is True
    assert result.page_count == 0
    assert result.pages == []


def test_text_page_is_classified_as_native_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    create_text_pdf(pdf_path)

    result = run_preflight(pdf_path)

    assert result.pages[0].page_type == "native_text"


def test_image_only_page_is_classified_as_scanned(tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    create_image_pdf(pdf_path)

    result = run_preflight(pdf_path)

    assert result.pages[0].page_type == "scanned"


def test_text_and_image_page_is_classified_as_mixed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mixed.pdf"
    create_image_pdf(pdf_path, text="Text plus image")

    result = run_preflight(pdf_path)

    assert result.pages[0].page_type == "mixed"
