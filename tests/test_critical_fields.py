from greatocr.model.critical_fields import detect_critical_fields
from greatocr.model.document import Block, Document, Page, TextSpan


def make_document(texts: list[tuple[str, float]]) -> Document:
    spans = [
        TextSpan(
            span_id=f"span-{index}",
            original_text=text,
            current_text=text,
            confidence=confidence,
        )
        for index, (text, confidence) in enumerate(texts, start=1)
    ]
    return Document(
        document_id="doc-1",
        source_file_name="sample.pdf",
        file_sha256="a" * 64,
        page_count=1,
        provider_name="fake",
        pages=[
            Page(
                page_id="page-0001",
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
                blocks=[
                    Block(
                        block_id="block-1",
                        block_type="paragraph",
                        reading_order=1,
                        spans=spans,
                    )
                ],
            )
        ],
    )


def test_detects_amount_date_tax_id_account_and_contract_number() -> None:
    document = make_document(
        [
            ("Amount: USD 1,200.00", 0.99),
            ("Date: 2026-06-25", 0.99),
            ("Tax ID: 91310000MA1K000000", 0.99),
            ("Account: 6222 8888 0000 1234", 0.99),
            ("Contract No. HT-2026-001", 0.99),
        ]
    )

    protected = detect_critical_fields(document)

    critical_types = [
        span.critical_type
        for span in protected.pages[0].blocks[0].spans
        if span.is_critical
    ]
    assert critical_types == ["amount", "date", "tax_id", "account", "contract_number"]


def test_critical_fields_are_not_rewritten_by_default() -> None:
    document = make_document([("Contract No. HT-2026-001", 0.99)])

    protected = detect_critical_fields(document)
    span = protected.pages[0].blocks[0].spans[0]

    assert span.current_text == "Contract No. HT-2026-001"
    assert span.modifications == []


def test_low_confidence_critical_field_creates_issue() -> None:
    document = make_document([("Amount: USD 1,2?0.00", 0.55)])

    protected = detect_critical_fields(document)

    assert protected.issues[0].issue_type == "critical_field_low_confidence"
    assert protected.issues[0].page_number == 1
    assert protected.issues[0].severity == "high"
