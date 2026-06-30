# GreatOCR V1 Baseline

Created: 2026-06-25

This baseline contains:
- result/: current V1 MinerU smoke output files
- greatocr-v1-source-snapshot.zip: source, tests, docs, skill, and scripts snapshot
- SHA256SUMS.txt: checksums for release files except SHA256SUMS.txt itself

Excluded from the source snapshot:
- MinerU API key.txt
- testsamples/
- outputs/
- releases/
- .pytest_cache/
- __pycache__ and *.pyc

Rollback note:
To roll back code manually, extract greatocr-v1-source-snapshot.zip into the workspace root after moving aside newer changed files.
