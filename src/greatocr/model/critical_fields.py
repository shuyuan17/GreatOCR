from __future__ import annotations

import re

from greatocr.model.document import Document, Issue


LOW_CONFIDENCE_THRESHOLD = 0.8

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tax_id", re.compile(r"\bTax\s*ID\s*:\s*[A-Z0-9]{12,24}\b", re.IGNORECASE)),
    ("account", re.compile(r"\bAccount\s*:\s*(?:\d[\s-]?){12,}\b", re.IGNORECASE)),
    (
        "contract_number",
        re.compile(r"\b(?:Contract\s+No\.?|合同编号)\s*[:：]?\s*[A-Za-z0-9-]{4,}\b", re.IGNORECASE),
    ),
    (
        "amount",
        re.compile(
            r"\b(?:USD|CNY|RMB)\s*\d[\d,]*(?:\.\d+)?\b|[￥$]\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "date",
        re.compile(r"\b\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?\b"),
    ),
]


def detect_critical_fields(document: Document) -> Document:
    protected = document.model_copy(deep=True)
    issue_index = len(protected.issues) + 1

    for page in protected.pages:
        for block in page.blocks:
            for span in block.spans:
                critical_type = _detect_type(span.current_text)
                if not critical_type:
                    continue

                span.is_critical = True
                span.critical_type = critical_type
                if span.confidence < LOW_CONFIDENCE_THRESHOLD:
                    protected.issues.append(
                        Issue(
                            issue_id=f"issue-critical-{issue_index:04d}",
                            page_number=page.page_number,
                            issue_type="critical_field_low_confidence",
                            severity="high",
                            message=f"Low confidence critical field: {critical_type}",
                            related_id=span.span_id,
                            snippet=span.current_text,
                            suggestion="Compare this value against the source PDF.",
                        )
                    )
                    issue_index += 1

    return protected


def _detect_type(text: str) -> str | None:
    for critical_type, pattern in _PATTERNS:
        if pattern.search(text):
            return critical_type
    return None
