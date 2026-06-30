import pytest

from greatocr.selection.page_ranges import PageRangeError, parse_page_ranges


def test_parse_mixed_ranges_deduplicates_and_preserves_document_order() -> None:
    selection = parse_page_ranges("3, 8-10, 9, 1", page_count=12)

    assert selection.pages == [1, 3, 8, 9, 10]
    assert selection.groups == [[3], [8, 9, 10], [9], [1]]


@pytest.mark.parametrize("value", ["0", "4-2", "13", "3,,4", "x"])
def test_invalid_ranges_are_rejected(value: str) -> None:
    with pytest.raises(PageRangeError, match=r"1\.\.12|empty|descending|invalid"):
        parse_page_ranges(value, page_count=12)


def test_empty_selection_is_rejected() -> None:
    with pytest.raises(PageRangeError, match="empty"):
        parse_page_ranges("", page_count=12)


def test_non_positive_document_page_count_is_rejected() -> None:
    with pytest.raises(PageRangeError, match="page_count"):
        parse_page_ranges("1", page_count=0)
