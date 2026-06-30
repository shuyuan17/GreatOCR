from pathlib import Path

import pytest

from greatocr.model.document import Block, Document, Page, Table, TableCell, TextSpan
from greatocr.rework import ReworkTargetNotFound, rework_pages, rework_tables


class PageReworkParser:
    def __init__(self) -> None:
        self.pages_seen: list[int] = []

    def parse_pages(self, source_pdf: Path, raw_result_dir: Path, pages: list[int]) -> dict:
        self.pages_seen.extend(pages)
        page_number = pages[0]
        return {
            "provider": {"name": "fake"},
            "document": {
                "pages": [
                    {
                        "page_number": page_number,
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": f"Reworked page {page_number}",
                            }
                        ],
                    }
                ]
            },
        }


class TableReworkParser(PageReworkParser):
    def parse_pages(self, source_pdf: Path, raw_result_dir: Path, pages: list[int]) -> dict:
        self.pages_seen.extend(pages)
        page_number = pages[0]
        return {
            "provider": {"name": "fake"},
            "document": {
                "pages": [
                    {
                        "page_number": page_number,
                        "blocks": [
                            {"type": "paragraph", "text": "Keep me"},
                            {
                                "type": "table",
                                "rows": [["Item", "Amount"], ["Updated", "200"]],
                            },
                        ],
                    }
                ]
            },
        }


def make_task(task_dir: Path) -> None:
    table = Table(
        table_id="table-p0005-b0002",
        rows=[[TableCell(text="Item"), TableCell(text="Amount")], [TableCell(text="Old"), TableCell(text="100")]],
    )
    document = Document(
        document_id="doc-1",
        source_file_name="sample.pdf",
        file_sha256="a" * 64,
        page_count=2,
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
                        block_id="block-p0001-paragraph-0001",
                        block_type="paragraph",
                        reading_order=1,
                        spans=[TextSpan(span_id="s1", original_text="Stable", current_text="Stable")],
                    )
                ],
            ),
            Page(
                page_id="page-0005",
                page_number=5,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
                blocks=[
                    Block(
                        block_id="block-p0005-paragraph-0001",
                        block_type="paragraph",
                        reading_order=1,
                        spans=[TextSpan(span_id="s5", original_text="Keep me", current_text="Keep me")],
                    ),
                    Block(
                        block_id="block-p0005-table-0002",
                        block_type="table",
                        reading_order=2,
                        table=table,
                    ),
                ],
            ),
        ],
    )
    intermediates = task_dir / "intermediates"
    intermediates.mkdir(parents=True)
    (task_dir / "sample.pdf").write_bytes(b"%PDF-1.7 sample")
    (intermediates / "document.json").write_text(document.model_dump_json(indent=2), encoding="utf-8")


def test_page_rework_calls_provider_only_for_requested_page(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    make_task(task_dir)
    parser = PageReworkParser()

    rework_pages(task_dir, [5], parser)

    assert parser.pages_seen == [5]


def test_page_rework_preserves_unaffected_page_block_ids(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    make_task(task_dir)

    updated = rework_pages(task_dir, [5], PageReworkParser())

    assert updated.pages[0].blocks[0].block_id == "block-p0001-paragraph-0001"


def test_page_rework_regenerates_outputs(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    make_task(task_dir)

    rework_pages(task_dir, [5], PageReworkParser())

    assert (task_dir / "intermediates" / "document.json").is_file()
    assert (task_dir / "result.docx").is_file()
    assert (task_dir / "quality-report.docx").is_file()


def test_table_rework_parses_table_page(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    make_task(task_dir)
    parser = TableReworkParser()

    rework_tables(task_dir, ["table-p0005-b0002"], parser)

    assert parser.pages_seen == [5]


def test_table_rework_replaces_only_target_table_block(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    make_task(task_dir)

    updated = rework_tables(task_dir, ["table-p0005-b0002"], TableReworkParser())
    page = next(page for page in updated.pages if page.page_number == 5)

    assert page.blocks[0].spans[0].current_text == "Keep me"
    assert page.blocks[1].table.rows[1][0].text == "Updated"


def test_missing_table_id_raises_clear_error(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    make_task(task_dir)

    with pytest.raises(ReworkTargetNotFound, match="missing-table"):
        rework_tables(task_dir, ["missing-table"], TableReworkParser())
