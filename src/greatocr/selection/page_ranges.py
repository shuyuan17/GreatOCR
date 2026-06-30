from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PageRangeError(ValueError):
    """Raised when a page selection expression is invalid."""


class PageSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    expression: str
    pages: list[int]
    groups: list[list[int]]


def parse_page_ranges(expression: str, page_count: int) -> PageSelection:
    if page_count < 1:
        raise PageRangeError("page_count must be at least 1")
    if not expression.strip():
        raise PageRangeError("empty page selection")

    groups: list[list[int]] = []
    for raw_token in expression.split(","):
        token = raw_token.strip()
        if not token:
            raise PageRangeError("empty page token")

        if "-" in token:
            parts = token.split("-")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise PageRangeError(f"invalid page range: {token}; expected 1..{page_count}")
            start, end = map(int, parts)
            if start > end:
                raise PageRangeError(f"descending page range: {token}; expected 1..{page_count}")
            group = list(range(start, end + 1))
        elif token.isdigit():
            group = [int(token)]
        else:
            raise PageRangeError(f"invalid page token: {token}; expected 1..{page_count}")

        if any(page < 1 or page > page_count for page in group):
            raise PageRangeError(f"page outside 1..{page_count}: {token}")
        groups.append(group)

    pages = sorted({page for group in groups for page in group})
    return PageSelection(expression=expression, pages=pages, groups=groups)
