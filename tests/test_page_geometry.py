import pytest

from greatocr.model.geometry import effective_page_size, normalize_bbox


def test_rotation_270_swaps_effective_page_size() -> None:
    assert effective_page_size(842, 595, 270) == (595, 842)


def test_bbox_is_normalized_to_zero_one() -> None:
    normalized = normalize_bbox([84.2, 59.5, 421, 297.5], 842, 595)

    assert normalized == pytest.approx([0.1, 0.1, 0.5, 0.5])
