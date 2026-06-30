# GreatOCR V1 Known Limitations

## Out Of Scope For V1

- Translation.
- Folder or batch processing.
- High-fidelity text-box-based Word reconstruction.
- Paragraph-level in-place DOCX replacement.
- Automatic installation or control of Microsoft Word.
- Automatic deployment of local large models.
- Pixel-level equivalence with the source PDF.

## Provider And Security

- MinerU API shape, quotas, retention policy, and data residency must be approved by the user or enterprise before real upload.
- Public provider upload is disabled for sensitive mode by default.
- This repository does not store provider credentials.

## Document Quality

- Complex financial tables may degrade or require manual review when confidence is low.
- Low-quality scans, handwriting, severe skew, or damaged pages may need manual correction.
- Missing fonts can change line breaks and pagination.
- Signatures, seals, and stamps are preserved as images and may not be editable text.

## Suggested V2 Priorities

1. Real MinerU contract mapping against approved sample outputs.
2. Richer table structure handling and visual fallback assets.
3. Word manual scoring workflow and fixture baselines.
4. More granular rework beyond V1 page/table scope.
5. Additional provider adapters behind the same `DocumentParser` contract.
