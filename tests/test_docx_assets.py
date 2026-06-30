from pathlib import Path
import shutil
from zipfile import ZipFile

import pytest
from PIL import Image
from docx import Document as WordDocument

from greatocr.docx.builder import build_docx
from greatocr.model.document import Asset, Block, Document, Page


def create_png(path: Path) -> None:
    Image.new("RGB", (24, 24), color="red").save(path)


def make_document(asset: Asset) -> Document:
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
                page_type="scanned",
                blocks=[
                    Block(
                        block_id="block-image",
                        block_type="image",
                        reading_order=1,
                        asset=asset,
                    )
                ],
            )
        ],
        assets=[asset],
    )


def test_image_asset_is_inserted_into_docx(tmp_path: Path) -> None:
    image_path = tmp_path / "image.png"
    create_png(image_path)
    asset = Asset(
        asset_id="image-1",
        asset_type="image",
        path=str(image_path),
        page_number=1,
    )

    result = build_docx(make_document(asset), tmp_path / "result.docx")
    names = ZipFile(result.output_path).namelist()

    assert any(name.startswith("word/media/") for name in names)


def test_missing_image_asset_generates_issue_without_stopping(tmp_path: Path) -> None:
    asset = Asset(
        asset_id="missing-1",
        asset_type="image",
        path=str(tmp_path / "missing.png"),
        page_number=1,
    )

    result = build_docx(make_document(asset), tmp_path / "result.docx")

    assert result.output_path.is_file()
    assert result.issues[0].issue_type == "asset_missing"


def test_signature_and_seal_are_preserved_as_images(tmp_path: Path) -> None:
    image_path = tmp_path / "signature.png"
    create_png(image_path)
    asset = Asset(
        asset_id="signature-1",
        asset_type="signature",
        path=str(image_path),
        page_number=1,
    )

    result = build_docx(make_document(asset), tmp_path / "result.docx")
    names = ZipFile(result.output_path).namelist()

    assert any(name.startswith("word/media/") for name in names)


def test_relative_asset_survives_task_directory_move(tmp_path: Path) -> None:
    task = tmp_path / "task-a"
    relative_path = Path("intermediates/assets/images/signature.png")
    image_path = task / relative_path
    image_path.parent.mkdir(parents=True)
    create_png(image_path)
    asset = Asset(
        asset_id="signature-portable",
        asset_type="image",
        path=relative_path.as_posix(),
        page_number=1,
        bbox=[0.1, 0.1, 0.6, 0.3],
    )
    document_path = task / "intermediates/document.json"
    document_path.write_text(make_document(asset).model_dump_json(), encoding="utf-8")

    moved = tmp_path / "task-b"
    shutil.move(task, moved)
    document = Document.model_validate_json(
        (moved / "intermediates/document.json").read_text(encoding="utf-8")
    )
    result = build_docx(document, moved / "result.docx", task_dir=moved)

    assert not [issue for issue in result.issues if issue.issue_type == "asset_missing"]
    assert any(name.startswith("word/media/") for name in ZipFile(result.output_path).namelist())


def test_image_width_follows_its_fraction_of_the_source_page(tmp_path: Path) -> None:
    image_path = tmp_path / "wide-image.png"
    create_png(image_path)
    asset = Asset(
        asset_id="wide-image",
        asset_type="image",
        path=str(image_path),
        page_number=1,
        bbox=[0.1, 0.1, 0.6, 0.3],
    )

    result = build_docx(make_document(asset), tmp_path / "proportional.docx")
    reopened = WordDocument(result.output_path)
    section = reopened.sections[0]
    expected_inches = (
        section.page_width - section.left_margin - section.right_margin
    ) / 914400 * 0.5

    assert reopened.inline_shapes[0].width.inches == pytest.approx(expected_inches, abs=0.02)
