from __future__ import annotations

import json
from pathlib import Path

from greatocr.model.document import Issue
from greatocr.validation.quality import QualitySummary


def write_quality_json(
    summary: QualitySummary,
    issues: list[Issue],
    output_path: Path,
) -> Path:
    payload = summary.model_dump(mode="json")
    payload["issues"] = [issue.model_dump(mode="json") for issue in issues]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
