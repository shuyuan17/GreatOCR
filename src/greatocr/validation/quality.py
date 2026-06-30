from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict

from greatocr.model.document import Document, Issue


QualityRating = Literal["high", "medium", "low"]


class QualitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_name: str
    page_count: int
    provider_name: str
    processed_at: datetime
    rating: QualityRating
    page_type_counts: dict[str, int]
    issue_count: int
    high_issue_count: int
    critical_issue_count: int
    table_degraded_count: int
    font_substitution_count: int = 0
    auto_correction_count: int = 0


def compute_quality_summary(document: Document, issues: list[Issue]) -> QualitySummary:
    page_type_counts = Counter(page.page_type for page in document.pages)
    high_issue_count = sum(1 for item in issues if item.severity == "high")
    critical_issue_count = sum(
        1 for item in issues if item.issue_type.startswith("critical_field")
    )
    table_degraded_count = sum(1 for item in issues if item.issue_type == "table_degraded")

    if high_issue_count:
        rating: QualityRating = "low"
    elif table_degraded_count >= 3:
        rating = "medium"
    else:
        rating = "high"

    return QualitySummary(
        file_name=document.source_file_name,
        page_count=document.page_count,
        provider_name=document.provider_name,
        processed_at=datetime.now(timezone.utc),
        rating=rating,
        page_type_counts=dict(page_type_counts),
        issue_count=len(issues),
        high_issue_count=high_issue_count,
        critical_issue_count=critical_issue_count,
        table_degraded_count=table_degraded_count,
    )
