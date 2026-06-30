from __future__ import annotations

from pathlib import Path

from docx.document import Document as WordDocument
from docx.shared import Inches

from greatocr.model.document import Asset, Issue


def add_image_asset(
    word: WordDocument,
    asset: Asset,
    page_number: int,
    *,
    task_dir: Path | None = None,
) -> list[Issue]:
    asset_path = _resolve_asset_path(asset.path, task_dir)
    if asset_path is None or not asset_path.exists():
        word.add_paragraph(f"[Missing {asset.asset_type}: {asset.asset_id}]")
        return [
            Issue(
                issue_id=f"issue-asset-missing-p{page_number:04d}-{asset.asset_id}",
                page_number=page_number,
                issue_type="asset_missing",
                severity="medium",
                message=f"Image asset is missing: {asset.asset_id}",
                related_id=asset.asset_id,
                suggestion="Check whether the provider exported this image asset.",
            )
        ]

    section = word.sections[-1]
    usable_width_inches = (
        section.page_width - section.left_margin - section.right_margin
    ) / 914400
    page_fraction = 0.25
    if asset.bbox and len(asset.bbox) == 4:
        page_fraction = max(0.05, min(1.0, asset.bbox[2] - asset.bbox[0]))
    word.add_picture(
        str(asset_path),
        width=Inches(usable_width_inches * page_fraction),
    )
    return []


def _resolve_asset_path(path: str | None, task_dir: Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if task_dir is None:
        return candidate

    task_root = task_dir.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (task_root / candidate).resolve()
    try:
        resolved.relative_to(task_root)
    except ValueError:
        return None
    return resolved
