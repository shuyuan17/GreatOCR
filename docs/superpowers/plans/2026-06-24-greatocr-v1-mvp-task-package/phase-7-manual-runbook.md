# Phase 7 Manual Runbook

## Steps

1. User provides one local PDF path.
2. Codex reads `skills/greatocr-document-reconstruction/references/default-questionnaire.md`.
3. Codex confirms any non-default choices, especially sensitive-file mode.
4. Codex runs:

```bash
python skills/greatocr-document-reconstruction/scripts/run_greatocr.py "<pdf-path>" --dry-run
```

5. Codex shows page count, page type summary, provider, data flow, and retention policy.
6. If a real external provider upload is required, Codex reads `references/security-policy.md` and gets explicit user confirmation.
7. Codex runs conversion through the GreatOCR CLI.
8. Codex reports output paths for `result.docx`, `quality-report.docx`, and retained intermediates.

## Pass Criteria

- No upload happens before explicit confirmation.
- Output paths are clear and local.
- Sensitive mode does not keep intermediate JSON by default.
- Failure messages explain the blocked step and the next action.
- No credentials, source document text, or private sample contents are copied into this runbook.
