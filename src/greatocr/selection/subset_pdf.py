from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader, PdfWriter

from greatocr.selection.page_ranges import PageSelection


class SubsetPdfResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    task_to_original: dict[int, int]


def write_subset_pdf(
    source: Path,
    pages: list[int],
    output: Path,
) -> SubsetPdfResult:
    if not pages:
        raise ValueError("at least one page must be selected")

    reader = PdfReader(source)
    invalid = [page for page in pages if page < 1 or page > len(reader.pages)]
    if invalid:
        raise ValueError(f"selected page outside 1..{len(reader.pages)}: {invalid[0]}")

    writer = PdfWriter()
    for page_number in pages:
        writer.add_page(reader.pages[page_number - 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        writer.write(stream)

    return SubsetPdfResult(
        path=output,
        task_to_original={index: page for index, page in enumerate(pages, start=1)},
    )


def output_groups(selection: PageSelection, *, split_by_group: bool) -> list[list[int]]:
    if not split_by_group:
        return [selection.pages]
    return [list(dict.fromkeys(group)) for group in selection.groups]
