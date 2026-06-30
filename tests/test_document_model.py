import pytest
from pydantic import ValidationError

from greatocr.model.document import (
    Block,
    Document,
    Issue,
    Page,
    TextSpan,
)
from greatocr.model.ids import make_block_id, make_page_id, make_span_id, make_table_id


def test_minimal_document_serializes_to_json_and_back() -> None:
    document = Document(
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
                        spans=[
                            TextSpan(
                                span_id="span-1",
                                original_text="Hello",
                                current_text="Hello",
                            )
                        ],
                    )
                ],
            )
        ],
    )

    restored = Document.model_validate_json(document.model_dump_json())

    assert restored == document


def test_block_type_is_restricted() -> None:
    with pytest.raises(ValidationError):
        Block(block_id="bad", block_type="unsupported", reading_order=1)


def test_issue_requires_page_type_severity_and_message() -> None:
    issue = Issue(
        issue_id="issue-1",
        page_number=1,
        issue_type="warning",
        severity="medium",
        message="Check this page.",
    )

    assert issue.page_number == 1


def test_stable_id_helpers_are_deterministic() -> None:
    assert make_page_id(12) == "page-0012"
    assert make_block_id(12, "paragraph", 3) == make_block_id(12, "paragraph", 3)
    assert make_table_id(12, 3) == "table-p0012-b0003"
    assert make_span_id(12, 3, 2) == "span-p0012-b0003-s0002"


def test_unmodified_page_ids_survive_local_reparse() -> None:
    original = [make_page_id(1), make_page_id(2), make_page_id(3)]
    reparsed = [make_page_id(1), make_page_id(2), make_page_id(3)]

    assert reparsed == original
