from __future__ import annotations


def effective_page_size(
    width: float,
    height: float,
    rotation: int,
) -> tuple[float, float]:
    return (height, width) if rotation % 180 else (width, height)


def normalize_bbox(
    bbox: list[float] | None,
    width: float,
    height: float,
) -> list[float] | None:
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    return [x0 / width, y0 / height, x1 / width, y1 / height]
