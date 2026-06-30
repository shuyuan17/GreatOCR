from __future__ import annotations


_CURRENCY_CODES = {"CNY", "USD", "RMB", "EUR", "GBP", "JPY"}


def join_line_fragments(left: str, right: str) -> str:
    left = left.rstrip()
    right = right.lstrip()
    if not left:
        return right
    if not right:
        return left
    if (
        left.endswith("-")
        and left[-2:-1].isascii()
        and left[-2:-1].isalpha()
        and right[:1].isascii()
        and right[:1].islower()
    ):
        return left[:-1] + right
    if left in _CURRENCY_CODES:
        return left + " " + right
    if (
        left[-1:].isascii()
        and right[:1].isascii()
        and left[-1:].isalnum()
        and right[:1].isalnum()
    ):
        return left + " " + right
    return left + right


def normalize_text(text: str) -> str:
    paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")
    normalized: list[str] = []
    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if not lines:
            normalized.append("")
            continue
        joined = lines[0]
        for line in lines[1:]:
            joined = join_line_fragments(joined, line)
        normalized.append(joined)
    return "\n\n".join(normalized)
