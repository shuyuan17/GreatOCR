# GreatOCR Product Vision

---

# Mission

GreatOCR is an AI Document Processing Platform.

It is NOT an OCR frontend.

---

# Core Architecture

Document
    ↓
OCR Provider
    ↓
AI Processing
    ↓
Outputs

---

# OCR Provider

Responsible for document recognition.

Current:

- MinerU

Future:

- Azure OCR
- Google Document AI
- OpenAI OCR

---

# AI Processing

Responsible for document enhancement.

Current:

- Translation

Future:

- Summary
- Rewrite
- Formatting
- Risk Check
- Glossary
- Table Optimization

---

# Product Principles

OCR and AI Processing are independent layers.

Any OCR Provider can work with any AI Engine.

The architecture should remain provider-agnostic.

---

# Demo Goal

Users should understand that GreatOCR is an AI workflow platform rather than a wrapper around a single OCR provider.

Every new feature should strengthen this positioning.