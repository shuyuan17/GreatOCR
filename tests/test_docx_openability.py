from pathlib import Path

from greatocr.docx.builder import build_docx
from greatocr.docx.validate_docx import validate_docx_package
from greatocr.model.document import Block, Document, Page, TextSpan


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
                blocks=[
                    Block(
                        block_id="block-1",
                        block_type="paragraph",
                        reading_order=1,
                        spans=[
                            TextSpan(
                                span_id="span-1",
                                original_text="Hello",
                                current_text="Hello",
                            )
                        ],
                    )
                ],
            )
        ],
    )


def test_valid_docx_package_returns_valid_true(tmp_path: Path) -> None:
    build_result = build_docx(make_document(), tmp_path / "result.docx")

    validation = validate_docx_package(build_result.output_path)

    assert validation.valid is True
    assert validation.issues == []


def test_corrupt_zip_returns_validation_issue(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.docx"
    corrupt.write_bytes(b"not a zip")

    validation = validate_docx_package(corrupt)

    assert validation.valid is False
    assert validation.issues[0].issue_type == "docx_invalid_package"
