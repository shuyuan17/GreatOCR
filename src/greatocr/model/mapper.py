from __future__ import annotations

from greatocr.ingest.preflight import PreflightResult
from greatocr.model.document import (
    Asset,
    Block,
    Document,
    Issue,
    Page,
    Table,
    TableCell,
    TextSpan,
)
from greatocr.model.ids import make_block_id, make_page_id, make_span_id, make_table_id
from greatocr.model.geometry import normalize_bbox


_TEXT_BLOCK_TYPES = {"title", "paragraph", "list"}


def map_provider_result(raw_result: dict, preflight: PreflightResult) -> Document:
    provider_name = raw_result.get("provider", {}).get("name", "unknown")
    raw_document = raw_result.get("document", {})
    preflight_pages = {page.page_number: page for page in preflight.pages}
    pages: list[Page] = []
    assets: list[Asset] = []
    issues: list[Issue] = []

    for raw_page in raw_document.get("pages", []):
        page_number = int(raw_page["page_number"])
        preflight_page = preflight_pages.get(page_number)
        blocks: list[Block] = []
        reading_order = 1

        if raw_page.get("header"):
            blocks.append(
                _text_block(
                    page_number,
                    "header",
                    reading_order,
                    raw_page["header"],
                    provider_name,
                )
            )
            reading_order += 1

        for raw_block in raw_page.get("blocks", []):
            block_type = raw_block.get("type")
            source_bbox = raw_block.get("bbox")
            bbox = (
                normalize_bbox(
                    source_bbox,
                    preflight_page.width,
                    preflight_page.height,
                )
                if preflight_page
                else source_bbox
            )
            if block_type in _TEXT_BLOCK_TYPES:
                blocks.append(
                    _text_block(
                        page_number,
                        block_type,
                        reading_order,
                        raw_block.get("text", ""),
                        provider_name,
                        bbox=bbox,
                        source_bbox=source_bbox,
                        confidence=float(raw_block.get("confidence", 1.0)),
                    )
                )
            elif block_type == "table":
                table = Table(
                    table_id=make_table_id(page_number, reading_order),
                    rows=[
                        [TableCell(text=str(cell)) for cell in row]
                        for row in raw_block.get("rows", [])
                    ],
                    confidence=float(raw_block.get("confidence", 1.0)),
                )
                blocks.append(
                    Block(
                        block_id=make_block_id(page_number, "table", reading_order),
                        block_type="table",
                        reading_order=reading_order,
                        table=table,
                        bbox=bbox,
                        source_bbox=source_bbox,
                        confidence=table.confidence,
                        source=provider_name,
                    )
                )
            elif block_type == "image":
                asset = Asset(
                    asset_id=raw_block.get("asset_id", f"asset-{page_number}-{reading_order}"),
                    asset_type="image",
                    path=raw_block.get("path"),
                    page_number=page_number,
                    bbox=bbox,
                    source_bbox=source_bbox,
                    content_fingerprint=raw_block.get("content_fingerprint"),
                )
                assets.append(asset)
                blocks.append(
                    Block(
                        block_id=make_block_id(page_number, "image", reading_order),
                        block_type="image",
                        reading_order=reading_order,
                        asset=asset,
                        bbox=bbox,
                        source_bbox=source_bbox,
                        confidence=float(raw_block.get("confidence", 1.0)),
                        source=provider_name,
                    )
                )
            else:
                issues.append(
                    Issue(
                        issue_id=f"issue-unknown-p{page_number:04d}-{reading_order:04d}",
                        page_number=page_number,
                        issue_type="unknown_provider_block",
                        severity="medium",
                        message=f"Unknown provider block type: {block_type}",
                    )
                )
            reading_order += 1

        if raw_page.get("footer"):
            blocks.append(
                _text_block(
                    page_number,
                    "footer",
                    reading_order,
                    raw_page["footer"],
                    provider_name,
                )
            )

        pages.append(
            Page(
                page_id=make_page_id(page_number),
                page_number=page_number,
                width=preflight_page.width if preflight_page else 0,
                height=preflight_page.height if preflight_page else 0,
                rotation=preflight_page.rotation if preflight_page else 0,
                page_type=preflight_page.page_type if preflight_page else "scanned",
                blocks=blocks,
            )
        )

    return Document(
        document_id=f"doc-{preflight.file_sha256[:12]}",
        source_file_name=preflight.source_path.name,
        file_sha256=preflight.file_sha256,
        page_count=preflight.page_count,
        provider_name=provider_name,
        pages=pages,
        assets=assets,
        issues=issues,
    )


def _text_block(
    page_number: int,
    block_type: str,
    reading_order: int,
    text: str,
    provider_name: str,
    *,
    bbox: list[float] | None = None,
    source_bbox: list[float] | None = None,
    confidence: float = 1.0,
) -> Block:
    return Block(
        block_id=make_block_id(page_number, block_type, reading_order),
        block_type=block_type,
        reading_order=reading_order,
        spans=[
            TextSpan(
                span_id=make_span_id(page_number, reading_order, 1),
                original_text=text,
                current_text=text,
                confidence=confidence,
                bbox=bbox,
                source_bbox=source_bbox,
            )
        ],
        bbox=bbox,
        source_bbox=source_bbox,
        confidence=confidence,
        source=provider_name,
    )
