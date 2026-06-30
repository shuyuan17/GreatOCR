# GreatOCR V1 Acceptance Report

## Automated Acceptance

| Check | Result | Evidence |
| --- | --- | --- |
| Full regression | passed | `python -m pytest` |
| Fake provider end-to-end | passed | `python scripts/run_acceptance.py --provider fake` |
| Required outputs | passed | `result.docx`, `quality-report.docx`, `intermediates/document.json` generated in fake acceptance |
| Sensitive retention | passed | Sensitive fake pipeline removes `intermediates/` after final outputs |
| Secret leakage checks | passed | Tests cover task outputs, provider errors, and quality report body text |

## Manual Word Checks

Manual Microsoft Word desktop checks are pending user execution.

| Sample | Opens Without Repair Prompt | Titles | Paragraphs | Tables | Images/Header/Footer | Pagination | Rework Estimate | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `testsamples/中文10页内.pdf` | pending | pending | pending | pending | pending | pending | pending | Requires real provider output for content fidelity |
| `testsamples/中英夹杂的.pdf` | pending | pending | pending | pending | pending | pending | pending | Requires real provider output for OCR fidelity |
| `testsamples/英语含表格的.pdf` | pending | pending | pending | pending | pending | pending | pending | Table editability must be checked manually |

## Current Conclusion

The local engine, fake provider path, output packaging, security gates, and report generation pass automated V1 acceptance. Real OCR quality and Word visual scoring require approved provider access and manual Word review.

