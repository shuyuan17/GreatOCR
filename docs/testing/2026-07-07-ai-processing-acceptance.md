# AI Processing MVP - Acceptance Test

---

# UI

- [ ] AI Processing section is visible.
- [ ] Default option is OCR Only.
- [ ] Translation can be selected.
- [ ] Target Language selector exists.
- [ ] Translation Mode selector exists.

---

# Settings

- [ ] DeepSeek configuration section exists.
- [ ] API Key can be saved.
- [ ] Base URL can be saved.
- [ ] Test Connection works.
- [ ] API Key is never displayed in plain text.

---

# Backend

- [ ] translation_enabled is received.
- [ ] target_language is received.
- [ ] translation_mode is received.

---

# Worker

Translation disabled

- [ ] Current OCR workflow remains unchanged.

Translation enabled

- [ ] DeepSeek is called.
- [ ] translated_result.docx is generated.

---

# Result Center

- [ ] result.docx is shown.
- [ ] translated_result.docx is shown.
- [ ] Output folder can be opened.

---

# Security

- [ ] API Key never appears in logs.
- [ ] API Key never appears in task manifest.
- [ ] Existing credential storage is reused.

---

# Regression

- [ ] Existing OCR workflow still works.
- [ ] Existing task center still works.
- [ ] Existing settings still work.