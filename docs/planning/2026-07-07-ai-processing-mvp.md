# GreatOCR - AI Processing MVP Planning

**Version:** V2.4 Planning
**Status:** Planning
**Owner:** Product
**Priority:** P0 (Demo Sprint)

---

# Background

Current GreatOCR workflow:

Document
    ↓
MinerU OCR
    ↓
Word

Although the product is usable, its value mainly comes from the OCR Provider (MinerU). GreatOCR itself is currently closer to an OCR frontend.

To improve product value and AI innovation, GreatOCR should evolve into an AI Document Processing Platform.

---

# Product Vision

GreatOCR is NOT an OCR tool.

GreatOCR is an AI Document Processing Platform.

Pipeline:

Document
    ↓
OCR Provider
(MinerU)
    ↓
AI Processing
(DeepSeek)
    ↓
Output Documents

OCR is only the first stage.

AI Processing is the core extensible capability.

---

# Goals

Implement the first AI Processing capability:

- Translation

This MVP is designed for demo purposes and future extensibility.

---

# Non Goals

This phase will NOT implement:

- Summary
- Rewrite
- Proofreading
- Risk Check
- Table Optimization
- Multiple AI Providers

The architecture should reserve space for future expansion.

---

# Product Principles

AI Processing must always happen AFTER OCR.

The OCR pipeline must remain unchanged.

Translation is an optional post-processing step.

---

# User Experience

New Task

OCR Provider
    MinerU

AI Processing

○ OCR Only

○ Translation

AI Engine

DeepSeek

Target Language

English

Translation Mode

Page by Page

---

Current implementation:

Target Language

Only:

- English

Translation Mode

Only:

- Page by Page

However, UI must support future options.

---

# Outputs

Current:

- result.docx

New:

- translated_result.docx

The original document and translated document remain separate.

---

# Future Roadmap

AI Processing will later support:

- Translation
- Summary
- Rewrite
- Formatting
- Table Optimization
- Risk Check
- Glossary