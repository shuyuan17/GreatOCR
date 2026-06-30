from __future__ import annotations

from pathlib import Path

from docx import Document as WordDocument
from docx.shared import Pt
from pydantic import BaseModel, ConfigDict

from greatocr.docx.assets import add_image_asset
from greatocr.docx.styles import configure_base_styles
from greatocr.docx.tables import add_table
from greatocr.model.document import Block, Document, Issue


class DocxBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_path: Path
    issues: list[Issue]


def build_docx(document: Document, output_path: Path) -> DocxBuildResult:
    word = WordDocument()
    configure_base_styles(word)
    issues: list[Issue] = []

    if document.pages:
        first_page = document.pages[0]
        section = word.sections[0]
        section.page_width = Pt(first_page.width)
        section.page_height = Pt(first_page.height)

    for page_index, page in enumerate(sorted(document.pages, key=lambda item: item.page_number)):
        if page_index > 0:
            word.add_page_break()
            issues.append(
                Issue(
                    issue_id=f"issue-pagination-{page.page_number:04d}",
                    page_number=page.page_number,
                    issue_type="pagination_may_drift",
                    severity="low",
                    message="DOCX pagination may drift from the source PDF.",
                )
            )

        for block in sorted(page.blocks, key=lambda item: item.reading_order):
            issues.extend(_add_block(word, block, page.page_number))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    word.save(output_path)
    return DocxBuildResult(output_path=output_path, issues=issues)


def _add_block(word, block: Block, page_number: int) -> list[Issue]:
    text = "".join(span.current_text for span in block.spans)
    if block.block_type == "title":
        word.add_heading(text, level=1)
    elif block.block_type == "list":
        word.add_paragraph(text, style="List Bullet")
    elif block.block_type == "header":
        word.add_paragraph(text, style="GreatOCR Header")
    elif block.block_type == "footer":
        word.add_paragraph(text, style="GreatOCR Footer")
    elif block.block_type in {"paragraph", "page_number"}:
        word.add_paragraph(text)
    elif block.block_type == "table":
        return add_table(word, block, page_number)
    elif block.block_type == "image" and block.asset:
        return add_image_asset(word, block.asset, page_number)
    return []
