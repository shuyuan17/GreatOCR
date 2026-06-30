from greatocr.model.document import Block, Document, Page, Table, TableCell, TextSpan
from greatocr.model.markdown_export import export_markdown


def make_document(blocks: list[Block]) -> Document:
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
                blocks=blocks,
            )
        ],
    )


def test_title_exports_as_markdown_heading() -> None:
    document = make_document(
        [
            Block(
                block_id="b1",
                block_type="title",
                reading_order=1,
                spans=[TextSpan(span_id="s1", original_text="Title", current_text="Title")],
            )
        ]
    )

    assert export_markdown(document).startswith("# Title")


def test_paragraphs_export_in_reading_order() -> None:
    document = make_document(
        [
            Block(
                block_id="b2",
                block_type="paragraph",
                reading_order=2,
                spans=[TextSpan(span_id="s2", original_text="Second", current_text="Second")],
            ),
            Block(
                block_id="b1",
                block_type="paragraph",
                reading_order=1,
                spans=[TextSpan(span_id="s1", original_text="First", current_text="First")],
            ),
        ]
    )

    assert export_markdown(document).splitlines()[:3] == ["First", "", "Second"]


def test_table_exports_as_markdown_table_with_merge_note() -> None:
    table = Table(
        table_id="t1",
        rows=[
            [TableCell(text="Item"), TableCell(text="Amount")],
            [TableCell(text="Service", col_span=2), TableCell(text="100.00")],
        ],
    )
    document = make_document(
        [Block(block_id="b1", block_type="table", reading_order=1, table=table)]
    )

    markdown = export_markdown(document)

    assert "| Item | Amount |" in markdown
    assert "| --- | --- |" in markdown
    assert "<!-- merged cell at row 2, column 1: rowspan=1 colspan=2 -->" in markdown
