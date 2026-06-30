import json
from pathlib import Path

from greatocr.model.document import Document, Issue, Page
from greatocr.reports.quality_json import write_quality_json
from greatocr.validation.quality import compute_quality_summary


def make_document() -> Document:
    return Document(
        document_id="doc-1",
        source_file_name="sample.pdf",
        file_sha256="a" * 64,
        page_count=2,
        provider_name="fake",
        pages=[
            Page(
                page_id="page-0001",
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
            ),
            Page(
                page_id="page-0002",
                page_number=2,
                width=612,
                height=792,
                rotation=0,
                page_type="scanned",
            ),
        ],
    )


def issue(issue_type: str, severity: str = "medium") -> Issue:
    return Issue(
        issue_id=f"issue-{issue_type}",
        page_number=1,
        issue_type=issue_type,
        severity=severity,
        message="Check this.",
        snippet="ABC",
        suggestion="Review manually.",
    )


def test_quality_summary_is_high_without_high_severity_issues() -> None:
    summary = compute_quality_summary(make_document(), [issue("minor", "low")])

    assert summary.rating == "high"


def test_critical_field_issue_is_counted_and_not_hidden() -> None:
    summary = compute_quality_summary(
        make_document(),
        [issue("critical_field_untracked_change", "high")],
    )

    assert summary.rating == "low"
    assert summary.critical_issue_count == 1
    assert summary.high_issue_count == 1


def test_many_table_degradations_lower_rating() -> None:
    summary = compute_quality_summary(
        make_document(),
        [issue("table_degraded"), issue("table_degraded"), issue("table_degraded")],
    )

    assert summary.rating == "medium"
    assert summary.table_degraded_count == 3


def test_quality_json_contains_metadata_and_page_stats(tmp_path: Path) -> None:
    summary = compute_quality_summary(make_document(), [])

    write_quality_json(summary, [], tmp_path / "quality-report.json")
    payload = json.loads((tmp_path / "quality-report.json").read_text(encoding="utf-8"))

    assert payload["file_name"] == "sample.pdf"
    assert payload["page_count"] == 2
    assert payload["provider_name"] == "fake"
    assert payload["page_type_counts"] == {"native_text": 1, "scanned": 1}
    assert "processed_at" in payload


def test_quality_json_issue_fields_are_complete(tmp_path: Path) -> None:
    summary = compute_quality_summary(make_document(), [issue("table_degraded")])

    write_quality_json(summary, [issue("table_degraded")], tmp_path / "quality-report.json")
    payload = json.loads((tmp_path / "quality-report.json").read_text(encoding="utf-8"))

    issue_payload = payload["issues"][0]
    assert {"page_number", "snippet", "issue_type", "message", "suggestion"} <= set(
        issue_payload
    )
