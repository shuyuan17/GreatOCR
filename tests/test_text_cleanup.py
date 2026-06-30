import pytest

from greatocr.model.text_cleanup import join_line_fragments, normalize_text


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("Board", "resolution", "Board resolution"),
        ("inter-", "national", "international"),
        ("人民币", "52,077", "人民币52,077"),
        ("CNY", "52,077", "CNY 52,077"),
    ],
)
def test_join_line_fragments(left: str, right: str, expected: str) -> None:
    assert join_line_fragments(left, right) == expected


def test_normalize_text_repairs_ocr_line_breaks_conservatively() -> None:
    assert normalize_text("Board\nresolution\ninter-\nnational") == (
        "Board resolution international"
    )


def test_normalize_text_keeps_blank_line_as_paragraph_boundary() -> None:
    assert normalize_text("First paragraph.\n\nSecond paragraph.") == (
        "First paragraph.\n\nSecond paragraph."
    )
