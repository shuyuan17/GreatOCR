from __future__ import annotations

import re
from pathlib import Path

from greatocr.ingest.preflight import PreflightResult
from greatocr.model.document import Document, Issue
from greatocr.model.geometry import effective_page_size
from greatocr.model.text_cleanup import normalize_text


def run_integrity_checks(
    document: Document,
    preflight: PreflightResult,
    *,
    task_dir: Path | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    issue_index = 1

    output_pages = {page.page_number for page in document.pages}
    for page in preflight.pages:
        if page.page_number not in output_pages:
            issues.append(
                Issue(
                    issue_id=f"issue-integrity-{issue_index:04d}",
                    page_number=page.page_number,
                    issue_type="missing_page",
                    severity="high",
                    message=f"Input page {page.page_number} is missing from the document model.",
                    suggestion="Re-run parsing for this page or insert it as an image fallback.",
                )
            )
            issue_index += 1

    for page in document.pages:
        preflight_page = next(
            (item for item in preflight.pages if item.page_number == page.page_number),
            None,
        )
        if preflight_page:
            expected_width, expected_height = effective_page_size(
                preflight_page.width,
                preflight_page.height,
                preflight_page.rotation,
            )
            expected_landscape = expected_width > expected_height
            actual_landscape = page.effective_width > page.effective_height
            if expected_landscape != actual_landscape:
                issues.append(
                    Issue(
                        issue_id=f"issue-integrity-{issue_index:04d}",
                        page_number=page.page_number,
                        issue_type="orientation_mismatch",
                        severity="high",
                        message="Output page orientation differs from the source page.",
                        suggestion="Rebuild this page using its normalized effective dimensions.",
                    )
                )
                issue_index += 1

        for block in page.blocks:
            for span in block.spans:
                if (
                    span.is_critical
                    and span.original_text != span.current_text
                    and not span.modifications
                ):
                    issues.append(
                        Issue(
                            issue_id=f"issue-integrity-{issue_index:04d}",
                            page_number=page.page_number,
                            issue_type="critical_field_untracked_change",
                            severity="high",
                            message="Critical field changed without a recorded modification basis.",
                            related_id=span.span_id,
                            snippet=span.original_text,
                            suggestion="Restore the original value or add a traceable correction record.",
                        )
                    )
                    issue_index += 1
                if (
                    re.search(r"[A-Za-z0-9]\r?\n[A-Za-z0-9]", span.original_text)
                    and normalize_text(span.original_text) != span.current_text
                ):
                    issues.append(
                        Issue(
                            issue_id=f"issue-integrity-{issue_index:04d}",
                            page_number=page.page_number,
                            issue_type="possible_english_word_join",
                            severity="low",
                            message="An OCR line boundary may have joined English words.",
                            related_id=span.span_id,
                            snippet=span.current_text,
                            suggestion="Review spacing near the original OCR line break.",
                        )
                    )
                    issue_index += 1

    for asset in document.assets:
        asset_path = _asset_path(asset.path, task_dir)
        if asset.path and (asset_path is None or not asset_path.exists()):
            issues.append(
                Issue(
                    issue_id=f"issue-integrity-{issue_index:04d}",
                    page_number=asset.page_number,
                    issue_type="asset_missing",
                    severity="medium",
                    message=f"Referenced asset file is missing: {asset.asset_id}",
                    related_id=asset.asset_id,
                    suggestion="Check provider asset export or regenerate the page fallback.",
                )
            )
            issue_index += 1

    return issues


def _asset_path(path: str | None, task_dir: Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if task_dir is None:
        return candidate
    root = task_dir.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved
