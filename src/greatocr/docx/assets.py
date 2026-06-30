from __future__ import annotations

from pathlib import Path

from docx.document import Document as WordDocument
from docx.shared import Inches

from greatocr.model.document import Asset, Issue


def add_image_asset(word: WordDocument, asset: Asset, page_number: int) -> list[Issue]:
    if not asset.path or not Path(asset.path).exists():
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

    word.add_picture(asset.path, width=Inches(1.5))
    return []
