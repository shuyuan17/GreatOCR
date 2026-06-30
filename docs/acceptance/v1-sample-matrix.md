# GreatOCR V1 Sample Matrix

| Sample | Type | Pages Observed | Sensitive | Upload Allowed | Key Acceptance Points | Expected Degradation |
| --- | --- | ---: | --- | --- | --- | --- |
| `testsamples/中文10页内.pdf` | Chinese scanned/business PDF | 4 | no | not approved for public upload | Preflight, scanned-page detection, local fake-provider pipeline | Complex layout may need provider OCR; fake run validates packaging only |
| `testsamples/中英夹杂的.pdf` | Mixed Chinese/English PDF | pending manual count | no | not approved for public upload | Language preservation, key-field protection, quality report readability | OCR confidence issues reported |
| `testsamples/英语含表格的.pdf` | English table document | pending manual count | no | not approved for public upload | Editable table reconstruction when provider table structure is reliable | Low-confidence tables degrade to issue/fallback |
| `testsamples/英文签字盖章有页眉的.pdf` | English document with header/signature/seal | pending manual count | no | not approved for public upload | Header/footer and image asset preservation | Signature/seal retained as image |
| `testsamples/中文盖章的.pdf` | Chinese stamped document | pending manual count | no | not approved for public upload | Stamp as image, key fields unchanged | Stamp text may not be editable |
| `testsamples/30页中文.pdf` | 30-page Chinese sample | pending manual count | no | not approved for public upload | Progress/checkpoint behavior, page count stability | Long-running provider parse may need resume |
| `testsamples/超长160多页中文.pdf` | Very long Chinese sample | pending manual count | no | not approved for public upload | Out-of-MVP stress reference only | V1 target is 1-30 pages, occasional 30-100 pages |

Public or third-party upload is not approved in this matrix. Real MinerU smoke requires a separate explicit approval.

