from pathlib import Path
from zipfile import ZipFile

from PIL import Image

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
