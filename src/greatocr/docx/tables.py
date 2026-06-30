from __future__ import annotations

from docx.document import Document as WordDocument

from greatocr.model.document import Block, Issue


TABLE_CONFIDENCE_THRESHOLD = 0.75


def add_table(word: WordDocument, block: Block, page_number: int) -> list[Issue]:
    if block.table is None:
        return []

    if block.table.confidence < TABLE_CONFIDENCE_THRESHOLD:
        return [
            Issue(
                issue_id=f"issue-table-degraded-p{page_number:04d}-{block.reading_order:04d}",
                page_number=page_number,
                issue_type="table_degraded",
                severity="high",
                message="Low-confidence table was not converted to an editable Word table.",
                related_id=block.table.table_id,
                suggestion="Compare this table against the source PDF.",
            )
        ]

    rows = block.table.rows
    if not rows:
        return []

    col_count = max(len(row) for row in rows)
    word_table = word.add_table(rows=len(rows), cols=col_count)
    word_table.style = "Table Grid"

    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(row):
            target = word_table.cell(row_index, col_index)
            target.text = cell.text
            if cell.col_span > 1:
                end_col = min(col_index + cell.col_span - 1, col_count - 1)
                target.merge(word_table.cell(row_index, end_col))

    return []
