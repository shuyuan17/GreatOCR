import json
from pathlib import Path

from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.model.mapper import map_provider_result


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


def make_preflight() -> PreflightResult:
    return PreflightResult(
        source_path=Path("sample.pdf"),
        file_sha256="a" * 64,
        encrypted=False,
        page_count=1,
        pages=[
            PagePreflight(
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
            )
        ],
    )


def test_fake_provider_blocks_map_to_unified_block_types() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    document = map_provider_result(raw, make_preflight())

    block_types = [block.block_type for block in document.pages[0].blocks]
    assert block_types == ["header", "title", "paragraph", "table", "image", "footer"]
    assert document.pages[0].blocks[1].spans[0].current_text == "Sample Contract"
    assert document.pages[0].blocks[3].table.rows[1][1].text == "100.00"
    assert document.pages[0].blocks[4].asset.asset_id == "signature-1"


def test_mapper_preserves_coordinates_confidence_and_provider_metadata() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    document = map_provider_result(raw, make_preflight())
    title = document.pages[0].blocks[1]

    assert document.provider_name == "fake"
    assert title.bbox == [72, 80, 320, 110]
    assert title.confidence == 0.98
    assert title.source == "fake"


def test_unknown_provider_block_creates_warning_issue() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["document"]["pages"][0]["blocks"].append({"type": "stamp", "text": "seal"})

    document = map_provider_result(raw, make_preflight())

    assert document.issues[0].issue_type == "unknown_provider_block"
    assert document.issues[0].severity == "medium"
    assert "stamp" in document.issues[0].message
