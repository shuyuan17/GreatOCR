from __future__ import annotations

from pathlib import Path

from greatocr.ingest.preflight import PreflightResult
from greatocr.model.document import Document, Issue


def run_integrity_checks(document: Document, preflight: PreflightResult) -> list[Issue]:
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

    for asset in document.assets:
        if asset.path and not Path(asset.path).exists():
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
