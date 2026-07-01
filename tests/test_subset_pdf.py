from pathlib import Path

from pypdf import PdfReader, PdfWriter

from greatocr.selection.page_ranges import parse_page_ranges
from greatocr.selection.subset_pdf import output_groups, write_subset_pdf


def make_numbered_pdf(path: Path, page_count: int) -> Path:
    writer = PdfWriter()
    for index in range(page_count):
        writer.add_blank_page(width=600 + index, height=800 + index)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_subset_pdf_contains_only_selected_pages(tmp_path: Path) -> None:
    source = make_numbered_pdf(tmp_path / "source.pdf", page_count=5)

    result = write_subset_pdf(source, [2, 5], tmp_path / "subset.pdf")

    reader = PdfReader(result.path)
    assert len(reader.pages) == 2
    assert float(reader.pages[0].mediabox.width) == 601
    assert float(reader.pages[1].mediabox.width) == 604
    assert result.task_to_original == {1: 2, 2: 5}


def test_requested_groups_can_produce_separate_outputs() -> None:
    selection = parse_page_ranges("3-5, 20-22", page_count=30)

    assert output_groups(selection, split_by_group=True) == [
        [3, 4, 5],
        [20, 21, 22],
    ]
    assert output_groups(selection, split_by_group=False) == [
        [3, 4, 5, 20, 21, 22]
    ]


def test_output_groups_deduplicates_pages_when_outputs_are_merged() -> None:
    selection = parse_page_ranges("3-5, 4", page_count=10)

    assert output_groups(selection, split_by_group=True) == [[3, 4, 5], [4]]
    assert output_groups(selection, split_by_group=False) == [[3, 4, 5]]
