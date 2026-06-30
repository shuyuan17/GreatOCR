from greatocr.model.document import Block
from greatocr.model.layout import order_blocks


def make_block(block_id: str, reading_order: int, bbox: list[float]) -> Block:
    return Block(
        block_id=block_id,
        block_type="paragraph",
        reading_order=reading_order,
        bbox=bbox,
    )


def test_two_column_blocks_read_left_column_before_right() -> None:
    blocks = [
        make_block("left-1", 1, [0.05, 0.10, 0.45, 0.20]),
        make_block("right-1", 2, [0.55, 0.12, 0.95, 0.22]),
        make_block("left-2", 3, [0.05, 0.30, 0.45, 0.40]),
    ]

    ordered = order_blocks(blocks)

    assert [block.block_id for block in ordered] == ["left-1", "left-2", "right-1"]


def test_uncertain_layout_keeps_provider_reading_order() -> None:
    blocks = [
        make_block("second", 2, [0.1, 0.30, 0.9, 0.40]),
        make_block("first", 1, [0.1, 0.10, 0.9, 0.20]),
    ]

    ordered = order_blocks(blocks)

    assert [block.block_id for block in ordered] == ["first", "second"]
