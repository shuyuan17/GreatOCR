import json

import httpx

from greatocr.model.document import Block, Document, Page, TextSpan
from greatocr.reasoning.base import (
    CorrectionProposal,
    TextReasoner,
    apply_corrections,
    run_reasoning_stage,
)
from greatocr.reasoning.openai_compatible import (
    OpenAICompatibleReasoner,
    OpenAIReasonerConfig,
)


def document_with_span(*, critical: bool = False) -> Document:
    return Document(
        document_id="doc-reasoning",
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
                page_type="scanned",
                blocks=[
                    Block(
                        block_id="block-1",
                        block_type="paragraph",
                        reading_order=1,
                        spans=[
                            TextSpan(
                                span_id="span-1",
                                original_text=(
                                    "CNY 52,077,455.23" if critical else "Boardresolution"
                                ),
                                current_text=(
                                    "CNY 52,077,455.23" if critical else "Boardresolution"
                                ),
                                is_critical=critical,
                                critical_type="amount" if critical else None,
                            )
                        ],
                    )
                ],
            )
        ],
    )


class CountingReasoner(TextReasoner):
    def __init__(self) -> None:
        self.calls = 0

    def propose(self, document: Document) -> list[CorrectionProposal]:
        self.calls += 1
        return []


def test_pipeline_does_not_call_reasoner_when_disabled() -> None:
    reasoner = CountingReasoner()

    result = run_reasoning_stage(document_with_span(), reasoner, enabled=False)

    assert reasoner.calls == 0
    assert result == document_with_span()


def test_reasoner_cannot_replace_unverified_critical_value() -> None:
    document = document_with_span(critical=True)
    proposal = CorrectionProposal(
        span_id="span-1",
        original_text="CNY 52,077,455.23",
        replacement_text="CNY 52,077,455.28",
        reason="possible OCR digit",
        confidence=0.99,
    )

    updated = apply_corrections(document, [proposal])

    assert updated.pages[0].blocks[0].spans[0].current_text == "CNY 52,077,455.23"
    assert "critical_field_correction_rejected" in {
        issue.issue_type for issue in updated.issues
    }


def test_accepted_correction_keeps_a_traceable_modification() -> None:
    document = document_with_span()
    proposal = CorrectionProposal(
        span_id="span-1",
        original_text="Boardresolution",
        replacement_text="Board resolution",
        reason="missing English word boundary",
        confidence=0.98,
    )

    updated = apply_corrections(document, [proposal])
    span = updated.pages[0].blocks[0].spans[0]

    assert span.current_text == "Board resolution"
    assert span.modifications[0]["source"] == "text_reasoner"
    assert span.modifications[0]["previous_text"] == "Boardresolution"


def test_stale_proposal_is_rejected_when_text_has_changed() -> None:
    document = document_with_span()
    proposal = CorrectionProposal(
        span_id="span-1",
        original_text="Different old text",
        replacement_text="Board resolution",
        reason="stale suggestion",
        confidence=0.99,
    )

    updated = apply_corrections(document, [proposal])

    assert updated.pages[0].blocks[0].spans[0].current_text == "Boardresolution"
    assert "stale_correction_rejected" in {issue.issue_type for issue in updated.issues}


def test_openai_compatible_reasoner_sends_text_spans_not_page_images() -> None:
    document = document_with_span()
    document.pages[0].blocks[0].spans[0].confidence = 0.55

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8")
        payload = json.loads(body)
        assert request.headers["Authorization"] == "Bearer local-secret"
        assert "span-1" in body
        assert "Boardresolution" in body
        assert "data:image" not in body
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                [
                                    {
                                        "span_id": "span-1",
                                        "original_text": "Boardresolution",
                                        "replacement_text": "Board resolution",
                                        "reason": "missing word boundary",
                                        "confidence": 0.98,
                                    }
                                ]
                            )
                        }
                    }
                ]
            },
        )

    reasoner = OpenAICompatibleReasoner(
        OpenAIReasonerConfig(
            endpoint="https://reasoner.example.test/v1/chat/completions",
            api_key="local-secret",
            model_name="reasoner-test",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    proposals = reasoner.propose(document)

    assert proposals[0].replacement_text == "Board resolution"
