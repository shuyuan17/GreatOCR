from __future__ import annotations

from pathlib import Path

from docx import Document as WordDocument
from docx.enum.section import WD_ORIENT, WD_SECTION
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

    for page_index, page in enumerate(sorted(document.pages, key=lambda item: item.page_number)):
        section = (
            word.sections[0]
            if page_index == 0
            else word.add_section(WD_SECTION.NEW_PAGE)
        )
        _configure_section(section, page)
        _write_page_furniture(section, page.blocks)

        if page_index > 0:
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
            if block.block_type in {"header", "footer"}:
                continue
            issues.extend(_add_block(word, block, page.page_number))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    word.save(output_path)
    return DocxBuildResult(output_path=output_path, issues=issues)


def _configure_section(section, page) -> None:
    section.page_width = Pt(page.effective_width)
    section.page_height = Pt(page.effective_height)
    section.orientation = (
        WD_ORIENT.LANDSCAPE
        if page.effective_width > page.effective_height
        else WD_ORIENT.PORTRAIT
    )


def _write_page_furniture(section, blocks: list[Block]) -> None:
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    headers = [block for block in blocks if block.block_type == "header"]
    footers = [block for block in blocks if block.block_type == "footer"]
    _write_story_part(section.header, headers)
    _write_story_part(section.footer, footers)


def _write_story_part(part, blocks: list[Block]) -> None:
    paragraphs = part.paragraphs
    first = paragraphs[0]
    if not blocks:
        first.text = ""
        return
    first.text = _block_text(blocks[0])
    for block in blocks[1:]:
        part.add_paragraph(_block_text(block))


def _block_text(block: Block) -> str:
    return "".join(span.current_text for span in block.spans)


def _add_block(word, block: Block, page_number: int) -> list[Issue]:
    text = _block_text(block)
    if block.block_type == "title":
        word.add_heading(text, level=1)
    elif block.block_type == "list":
        word.add_paragraph(text, style="List Bullet")
    elif block.block_type in {"paragraph", "page_number"}:
        word.add_paragraph(text)
    elif block.block_type == "table":
        return add_table(word, block, page_number)
    elif block.block_type == "image" and block.asset:
        return add_image_asset(word, block.asset, page_number)
    return []
