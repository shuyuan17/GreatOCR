from __future__ import annotations

from typing import Literal

from pypdf import PageObject


PageType = Literal["native_text", "scanned", "mixed"]


def classify_page(page: PageObject) -> PageType:
    text = (page.extract_text() or "").strip()
    has_text = bool(text)
    has_images = bool(page.images)

    if has_text and has_images:
        return "mixed"
    if has_text:
        return "native_text"
    return "scanned"

