import json
from pathlib import Path
from zipfile import ZipFile

from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.model.mapper import map_provider_result
from greatocr.providers.mineru_zip import load_mineru_zip_result


def make_zip(path: Path) -> None:
    content = [
        {
            "type": "text",
            "text": "Main Title",
            "text_level": 1,
            "page_idx": 0,
            "bbox": [10, 20, 200, 50],
        },
        {
            "type": "text",
            "text": "First paragraph.",
            "page_idx": 0,
            "bbox": [10, 70, 200, 90],
        },
        {
            "type": "image",
            "img_path": "images/signature.jpg",
            "page_idx": 0,
            "bbox": [10, 120, 90, 180],
        },
        {
            "type": "table",
            "table_body": "<table><tr><td>Item</td><td>Amount</td></tr><tr><td>A</td><td>100</td></tr></table>",
            "page_idx": 1,
            "bbox": [10, 30, 250, 120],
        },
    ]
    with ZipFile(path, "w") as zf:
        zf.writestr("abc_content_list.json", json.dumps(content))
        zf.writestr("full.md", "# Main Title\n")
        zf.writestr("images/signature.jpg", b"fake-image-bytes")


def make_preflight() -> PreflightResult:
    return PreflightResult(
        source_path=Path("sample.pdf"),
        file_sha256="a" * 64,
        encrypted=False,
        page_count=2,
        pages=[
            PagePreflight(
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="scanned",
            ),
            PagePreflight(
                page_number=2,
                width=612,
                height=792,
                rotation=0,
                page_type="scanned",
            ),
        ],
    )


def test_load_mineru_zip_result_normalizes_content_list(tmp_path: Path) -> None:
    zip_path = tmp_path / "result.zip"
    make_zip(zip_path)

    raw = load_mineru_zip_result(zip_path, tmp_path / "assets")

    assert raw["provider"]["name"] == "mineru"
    assert raw["document"]["pages"][0]["blocks"][0]["type"] == "title"
    assert raw["document"]["pages"][0]["blocks"][1]["type"] == "paragraph"
    assert raw["document"]["pages"][0]["blocks"][2]["type"] == "image"
    assert raw["document"]["pages"][1]["blocks"][0]["rows"][1] == ["A", "100"]
    assert (tmp_path / "assets" / "images" / "signature.jpg").is_file()


def test_mineru_zip_result_maps_to_unified_document(tmp_path: Path) -> None:
    zip_path = tmp_path / "result.zip"
    make_zip(zip_path)

    document = map_provider_result(load_mineru_zip_result(zip_path, tmp_path / "assets"), make_preflight())

    assert document.provider_name == "mineru"
    assert document.pages[0].blocks[0].block_type == "title"
    assert document.pages[0].blocks[2].asset.path.endswith("signature.jpg")
    assert document.pages[1].blocks[0].table.rows[1][1].text == "100"
