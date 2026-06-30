from __future__ import annotations

from greatocr.model.document import Block, Document, Table


def export_markdown(document: Document) -> str:
    sections: list[str] = []
    for page in sorted(document.pages, key=lambda item: item.page_number):
        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            rendered = _render_block(block)
            if rendered:
                sections.append(rendered)
    return "\n\n".join(sections).rstrip() + "\n"


def _render_block(block: Block) -> str:
    if block.block_type == "title":
        return f"# {_span_text(block)}"
    if block.block_type in {"paragraph", "header", "footer", "page_number", "list"}:
        return _span_text(block)
    if block.block_type == "table" and block.table:
        return _render_table(block.table)
    if block.block_type == "image" and block.asset:
        return f"![{block.asset.asset_type}]({block.asset.asset_id})"
    return ""


def _span_text(block: Block) -> str:
    return "".join(span.current_text for span in block.spans)


def _render_table(table: Table) -> str:
    if not table.rows:
        return ""

    lines: list[str] = []
    header = [_escape_cell(cell.text) for cell in table.rows[0]]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")

    for row_index, row in enumerate(table.rows[1:], start=2):
        lines.append("| " + " | ".join(_escape_cell(cell.text) for cell in row) + " |")
        for col_index, cell in enumerate(row, start=1):
            if cell.row_span > 1 or cell.col_span > 1:
                lines.append(
                    "<!-- merged cell at row "
                    f"{row_index}, column {col_index}: "
                    f"rowspan={cell.row_span} colspan={cell.col_span} -->"
                )

    return "\n".join(lines)


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|")
