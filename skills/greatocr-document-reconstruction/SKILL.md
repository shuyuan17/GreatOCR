---
name: greatocr-document-reconstruction
description: Convert a single local PDF into editable DOCX outputs with GreatOCR. Use when Codex needs to guide a user through PDF preflight, safety confirmation, local conversion, quality reporting, checkpoint resume, or limited page/table rework for GreatOCR documents.
---

# GreatOCR Document Reconstruction

Use this skill to run the local GreatOCR engine for one PDF at a time.

## Workflow

1. Read `references/default-questionnaire.md` before starting conversion.
2. Ask only for values the user has not already provided.
3. Run a dry run first:

```bash
python skills/greatocr-document-reconstruction/scripts/run_greatocr.py "<pdf-path>" --dry-run
```

4. Show the preflight summary, provider, upload/data-flow summary, and retention policy.
5. If external upload is needed, read `references/security-policy.md` and get explicit user confirmation before any real provider call.
6. Run conversion through the local CLI, then report output paths:
   - `result.docx`
   - `quality-report.docx`
   - `intermediates/document.json`
   - `intermediates/content.md`
   - `intermediates/task-manifest.json`

## Safety

- Never write provider credentials into code, task directories, logs, tests, or reports.
- Never upload user files to a public or third-party provider without explicit confirmation.
- Treat sensitive files as public-provider-disabled by default.
- Do not bypass PDF passwords or access controls.

## Rework

For V1 rework, only use page-level or table-level reprocessing:

```bash
python -m greatocr.cli rework --task-dir "<task-dir>" --pages 5
python -m greatocr.cli rework --task-dir "<task-dir>" --tables table-p0005-b0002
```

Do not promise paragraph-level replacement or in-place DOCX patching.

