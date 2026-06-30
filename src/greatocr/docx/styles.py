from __future__ import annotations

from docx.document import Document as WordDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Pt


def configure_base_styles(document: WordDocument) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    if "GreatOCR Header" not in document.styles:
        header = document.styles.add_style("GreatOCR Header", WD_STYLE_TYPE.PARAGRAPH)
        header.font.size = Pt(9)
        header.font.italic = True

    if "GreatOCR Footer" not in document.styles:
        footer = document.styles.add_style("GreatOCR Footer", WD_STYLE_TYPE.PARAGRAPH)
        footer.font.size = Pt(9)
        footer.font.italic = True

