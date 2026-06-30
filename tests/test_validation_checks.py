from pathlib import Path

from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.model.document import Asset, Block, Document, Page, TextSpan
from greatocr.validation.checks import run_integrity_checks


def make_preflight(page_count: int = 1) -> PreflightResult:
    return PreflightResult(
        source_path=Path("sample.pdf"),
        file_sha256="a" * 64,
        encrypted=False,
        page_count=page_count,
        pages=[
            PagePreflight(
                page_number=index,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
            )
            for index in range(1, page_count + 1)
        ],
    )


def make_document(pages: list[Page], assets: list[Asset] | None = None) -> Document:
    return Document(
        document_id="doc-1",
        source_file_name="sample.pdf",
        file_sha256="a" * 64,
        page_count=len(pages),
        provider_name="fake",
        pages=pages,
        assets=assets or [],
    )


def test_missing_page_generates_issue() -> None:
    document = make_document(
        [
            Page(
                page_id="page-0001",
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
            )
        ]
    )

    issues = run_integrity_checks(document, make_preflight(page_count=3))

    assert issues[0].issue_type == "missing_page"
    assert issues[0].page_number == 2


def test_untracked_critical_field_difference_is_high_severity() -> None:
    span = TextSpan(
        span_id="span-1",
        original_text="USD 1,200.00",
        current_text="USD 120.00",
        is_critical=True,
        critical_type="amount",
    )
    document = make_document(
        [
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
                        spans=[span],
                    )
                ],
            )
        ]
    )

    issues = run_integrity_checks(document, make_preflight())

    assert issues[0].issue_type == "critical_field_untracked_change"
    assert issues[0].severity == "high"


def test_missing_image_asset_generates_issue(tmp_path: Path) -> None:
    asset = Asset(
        asset_id="asset-1",
        asset_type="image",
        path=str(tmp_path / "missing.png"),
        page_number=1,
    )
    document = make_document(
        [
            Page(
                page_id="page-0001",
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="scanned",
            )
        ],
        assets=[asset],
    )

    issues = run_integrity_checks(document, make_preflight())

    assert issues[0].issue_type == "asset_missing"
    assert issues[0].related_id == "asset-1"


def test_integrity_checks_report_orientation_asset_and_word_join_risks(
    tmp_path: Path,
) -> None:
    asset = Asset(
        asset_id="missing-relative",
        asset_type="image",
        path="intermediates/assets/images/missing.png",
        page_number=1,
    )
    page = Page(
        page_id="page-0001",
        page_number=1,
        width=612,
        height=792,
        effective_width=792,
        effective_height=612,
        rotation=0,
        page_type="scanned",
        blocks=[
            Block(
                block_id="block-joined",
                block_type="paragraph",
                reading_order=1,
                spans=[
                    TextSpan(
                        span_id="span-joined",
                        original_text="Board\nresolution",
                        current_text="Boardresolution",
                    )
                ],
            )
        ],
    )

    issues = run_integrity_checks(
        make_document([page], assets=[asset]),
        make_preflight(),
        task_dir=tmp_path,
    )

    assert {issue.issue_type for issue in issues} >= {
        "orientation_mismatch",
        "asset_missing",
        "possible_english_word_join",
    }
