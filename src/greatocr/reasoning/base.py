from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from greatocr.model.document import Document, Issue, TextSpan


class CorrectionProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    span_id: str
    original_text: str
    replacement_text: str
    reason: str
    confidence: float = Field(ge=0, le=1)


class TextReasoner(ABC):
    @abstractmethod
    def propose(self, document: Document) -> list[CorrectionProposal]:
        """Return corrections without mutating the supplied document."""


def run_reasoning_stage(
    document: Document,
    reasoner: TextReasoner,
    *,
    enabled: bool,
) -> Document:
    if not enabled:
        return document
    return apply_corrections(document, reasoner.propose(document))


def apply_corrections(
    document: Document,
    proposals: list[CorrectionProposal],
) -> Document:
    updated = document.model_copy(deep=True)
    spans = _span_index(updated)
    issues = list(updated.issues)

    for index, proposal in enumerate(proposals, start=1):
        location = spans.get(proposal.span_id)
        if location is None:
            issues.append(
                _issue(
                    index,
                    page_number=0,
                    issue_type="unknown_correction_span",
                    message="Text reasoner referenced a span that does not exist.",
                    proposal=proposal,
                )
            )
            continue
        page_number, span = location
        if proposal.original_text != span.current_text:
            issues.append(
                _issue(
                    index,
                    page_number=page_number,
                    issue_type="stale_correction_rejected",
                    message="Text reasoner proposal no longer matches the current text.",
                    proposal=proposal,
                )
            )
            continue
        if span.is_critical:
            issues.append(
                _issue(
                    index,
                    page_number=page_number,
                    issue_type="critical_field_correction_rejected",
                    message="Automatic correction of a critical field was rejected.",
                    proposal=proposal,
                )
            )
            continue

        previous = span.current_text
        span.current_text = proposal.replacement_text
        span.modifications.append(
            {
                "source": "text_reasoner",
                "previous_text": previous,
                "replacement_text": proposal.replacement_text,
                "reason": proposal.reason,
                "confidence": str(proposal.confidence),
            }
        )

    updated.issues = issues
    return updated


def _span_index(document: Document) -> dict[str, tuple[int, TextSpan]]:
    return {
        span.span_id: (page.page_number, span)
        for page in document.pages
        for block in page.blocks
        for span in block.spans
    }


def _issue(
    index: int,
    *,
    page_number: int,
    issue_type: str,
    message: str,
    proposal: CorrectionProposal,
) -> Issue:
    return Issue(
        issue_id=f"issue-reasoning-{index:04d}",
        page_number=page_number,
        issue_type=issue_type,
        severity="medium",
        message=message,
        related_id=proposal.span_id,
        snippet=proposal.original_text,
        suggestion="Review the proposed correction manually.",
    )
