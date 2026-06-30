from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from greatocr.ingest.page_classifier import PageType, classify_page


class InputFileNotFound(FileNotFoundError):
    """Raised when the requested input file does not exist."""


class InvalidPdfError(ValueError):
    """Raised when a file cannot be treated as a PDF."""


class PagePreflight(BaseModel):
    page_number: int
    width: float
    height: float
    rotation: int
    page_type: PageType


class PreflightResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: Path
    file_sha256: str
    encrypted: bool
    page_count: int
    pages: list[PagePreflight]


def run_preflight(pdf_path: Path) -> PreflightResult:
    if not pdf_path.exists():
        raise InputFileNotFound(f"input file does not exist: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise InvalidPdfError(f"expected a .pdf file: {pdf_path}")

    pdf_bytes = pdf_path.read_bytes()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise InvalidPdfError(f"invalid PDF header: {pdf_path}")

    file_sha256 = sha256(pdf_bytes).hexdigest()
    try:
        reader = PdfReader(str(pdf_path))
    except PdfReadError as exc:
        raise InvalidPdfError(f"could not read PDF: {pdf_path}") from exc

    if reader.is_encrypted:
        return PreflightResult(
            source_path=pdf_path,
            file_sha256=file_sha256,
            encrypted=True,
            page_count=0,
            pages=[],
        )

    pages: list[PagePreflight] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(
            PagePreflight(
                page_number=index,
                width=float(page.mediabox.width),
                height=float(page.mediabox.height),
                rotation=int(page.rotation or 0),
                page_type=classify_page(page),
            )
        )

    return PreflightResult(
        source_path=pdf_path,
        file_sha256=file_sha256,
        encrypted=False,
        page_count=len(pages),
        pages=pages,
    )
