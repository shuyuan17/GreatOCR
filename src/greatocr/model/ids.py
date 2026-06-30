from __future__ import annotations


def make_page_id(page_number: int) -> str:
    return f"page-{page_number:04d}"


def make_block_id(page_number: int, block_type: str, reading_order: int) -> str:
    return f"block-p{page_number:04d}-{block_type}-{reading_order:04d}"


def make_table_id(page_number: int, reading_order: int) -> str:
    return f"table-p{page_number:04d}-b{reading_order:04d}"


def make_span_id(page_number: int, reading_order: int, span_index: int) -> str:
    return f"span-p{page_number:04d}-b{reading_order:04d}-s{span_index:04d}"

