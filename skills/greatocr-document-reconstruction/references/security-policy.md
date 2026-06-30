# Security Policy

## Normal Mode

- The user may reuse a previously approved provider.
- Send files only to the selected and approved provider.
- Keep `document.json`, `content.md`, and `quality-report.json` unless the user asks to clean them.

## Sensitive Mode

- Confirm data flow for every task.
- Disable public providers by default.
- Allow only explicitly approved private endpoints or local processing.
- Keep only `result.docx` and `quality-report.docx` by default.

## Hard Rules

- Show provider name, endpoint type, and upload destination before any real upload.
- Do not store credentials in source code, generated reports, task manifests, logs, or fixtures.
- Do not bypass PDF passwords or access controls.
- Do not upload files to unapproved transfer or storage services.

