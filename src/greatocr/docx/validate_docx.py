from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict

from greatocr.model.document import Issue


class DocxValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    issues: list[Issue]


def validate_docx_package(path: Path) -> DocxValidationResult:
    required = {"[Content_Types].xml", "word/document.xml"}
    try:
        with ZipFile(path) as package:
            names = set(package.namelist())
    except (BadZipFile, FileNotFoundError) as exc:
        return DocxValidationResult(
            valid=False,
            issues=[
                Issue(
                    issue_id="issue-docx-invalid-package",
                    page_number=0,
                    issue_type="docx_invalid_package",
                    severity="high",
                    message=f"DOCX package cannot be opened: {type(exc).__name__}",
                )
            ],
        )

    missing = sorted(required - names)
    if missing:
        return DocxValidationResult(
            valid=False,
            issues=[
                Issue(
                    issue_id="issue-docx-missing-parts",
                    page_number=0,
                    issue_type="docx_missing_required_part",
                    severity="high",
                    message="DOCX package is missing required parts: " + ", ".join(missing),
                )
            ],
        )

    return DocxValidationResult(valid=True, issues=[])
