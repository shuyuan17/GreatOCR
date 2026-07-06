# GreatOCR - AI Processing MVP Work Plan

---

# Phase 1 - UI

Estimated: 30~60 min

## Task

Add AI Processing section to New Task page.

Options:

- OCR Only
- Translation

Show:

- AI Engine
- Target Language
- Translation Mode

No backend changes.

No API calls.

---

# Phase 2 - Task Schema

Estimated: 30 min

Add new task fields.

translation_enabled

target_language

translation_mode

Frontend and backend can exchange these fields.

Worker ignores them for now.

---

# Phase 3 - Settings

Estimated: 30~60 min

Add AI Engine settings.

DeepSeek

Fields:

- Base URL
- API Key
- Test Connection

Reuse existing secure credential storage.

---

# Phase 4 - Worker

Estimated: 1~2 hours

If translation_enabled == false

Current workflow remains unchanged.

If translation_enabled == true

OCR
    ↓
Read OCR Result
    ↓
DeepSeek Translation
    ↓
translated_result.docx

---

# Phase 5 - Result Center

Estimated: 30 min

Show:

- result.docx
- translated_result.docx

Support opening output folder.

---

# Development Rules

Each phase should be independently mergeable.

No phase should break the current OCR workflow.

Every phase must pass existing tests.