from __future__ import annotations

from greatocr.model.document import Block


def order_blocks(blocks: list[Block]) -> list[Block]:
    provider_order = sorted(blocks, key=lambda block: block.reading_order)
    if len(provider_order) < 2 or any(not _usable_bbox(block.bbox) for block in provider_order):
        return provider_order

    narrow = [block for block in provider_order if _width(block) <= 0.6]
    if len(narrow) != len(provider_order):
        return provider_order

    left = [block for block in narrow if _center_x(block) < 0.5]
    right = [block for block in narrow if _center_x(block) >= 0.5]
    if not left or not right:
        return provider_order
    if max(block.bbox[2] for block in left) > min(block.bbox[0] for block in right):
        return provider_order

    return [
        *sorted(left, key=lambda block: (block.bbox[1], block.bbox[0])),
        *sorted(right, key=lambda block: (block.bbox[1], block.bbox[0])),
    ]


def _usable_bbox(bbox: list[float] | None) -> bool:
    return bool(bbox and len(bbox) == 4 and bbox[2] >= bbox[0] and bbox[3] >= bbox[1])


def _width(block: Block) -> float:
    return block.bbox[2] - block.bbox[0]


def _center_x(block: Block) -> float:
    return (block.bbox[0] + block.bbox[2]) / 2
