from __future__ import annotations

from pathlib import Path

from greatocr.docx.builder import build_docx
from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.model.document import Block, Document, Page
from greatocr.model.mapper import map_provider_result
from greatocr.model.markdown_export import export_markdown
from greatocr.reports.quality_docx import write_quality_docx
from greatocr.validation.quality import compute_quality_summary


class ReworkTargetNotFound(ValueError):
    """Raised when a requested rework page/table cannot be found."""


def rework_pages(task_dir: Path, pages: list[int], parser) -> Document:
    document = _load_document(task_dir)
    raw = _parse_pages(task_dir, document, pages, parser)
    reworked = map_provider_result(raw, _preflight_from_document(document))
    page_map = {page.page_number: page for page in document.pages}
    for page in reworked.pages:
        page_map[page.page_number] = page
    updated = document.model_copy(
        update={"pages": [page_map[number] for number in sorted(page_map)]},
        deep=True,
    )
    _write_rework_outputs(task_dir, updated)
    return updated


def rework_tables(task_dir: Path, table_ids: list[str], parser) -> Document:
    document = _load_document(task_dir)
    table_locations = _find_tables(document)
    missing = [table_id for table_id in table_ids if table_id not in table_locations]
    if missing:
        raise ReworkTargetNotFound(", ".join(missing))

    pages = sorted({table_locations[table_id][0].page_number for table_id in table_ids})
    raw = _parse_pages(task_dir, document, pages, parser)
    reworked = map_provider_result(raw, _preflight_from_document(document))
    replacement_tables = _find_tables(reworked)

    updated_pages: list[Page] = []
    for page in document.pages:
        blocks: list[Block] = []
        for block in page.blocks:
            table_id = block.table.table_id if block.table else None
            if table_id in table_ids and table_id in replacement_tables:
                blocks.append(replacement_tables[table_id][1])
            else:
                blocks.append(block)
        updated_pages.append(page.model_copy(update={"blocks": blocks}, deep=True))

    updated = document.model_copy(update={"pages": updated_pages}, deep=True)
    _write_rework_outputs(task_dir, updated)
    return updated


def _load_document(task_dir: Path) -> Document:
    path = task_dir / "intermediates" / "document.json"
    return Document.model_validate_json(path.read_text(encoding="utf-8"))


def _parse_pages(task_dir: Path, document: Document, pages: list[int], parser) -> dict:
    raw_result_dir = task_dir / "intermediates" / "provider-raw-rework"
    source_pdf = task_dir / document.source_file_name
    if hasattr(parser, "parse_pages"):
        return parser.parse_pages(source_pdf, raw_result_dir, pages)
    result = parser.parse_document(source_pdf, raw_result_dir)
    import json

    return json.loads((result.raw_result_dir / "result.json").read_text(encoding="utf-8"))


def _preflight_from_document(document: Document) -> PreflightResult:
    return PreflightResult(
        source_path=Path(document.source_file_name),
        file_sha256=document.file_sha256,
        encrypted=False,
        page_count=document.page_count,
        pages=[
            PagePreflight(
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                rotation=page.rotation,
                page_type=page.page_type,
            )
            for page in document.pages
        ],
    )


def _find_tables(document: Document) -> dict[str, tuple[Page, Block]]:
    found: dict[str, tuple[Page, Block]] = {}
    for page in document.pages:
        for block in page.blocks:
            if block.table:
                found[block.table.table_id] = (page, block)
    return found


def _write_rework_outputs(task_dir: Path, document: Document) -> None:
    intermediates = task_dir / "intermediates"
    intermediates.mkdir(parents=True, exist_ok=True)
    (intermediates / "document.json").write_text(
        document.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (intermediates / "content.md").write_text(export_markdown(document), encoding="utf-8")
    build_docx(document, task_dir / "result.docx", task_dir=task_dir)
    summary = compute_quality_summary(document, document.issues)
    write_quality_docx(summary, document.issues, task_dir / "quality-report.docx")
