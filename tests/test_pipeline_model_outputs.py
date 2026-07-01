from pathlib import Path
import json
from zipfile import ZipFile

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import PagePreflight, PreflightResult
from greatocr.pipeline import run_docx_stage, run_model_stage, run_parse_stage
from greatocr.providers.base import ParserJobResult
from greatocr.providers.fake import FakeDocumentParser
from greatocr.security import build_data_flow_summary


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


def make_preflight(tmp_path: Path) -> PreflightResult:
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    return PreflightResult(
        source_path=source_pdf,
        file_sha256="a" * 64,
        encrypted=False,
        page_count=1,
        pages=[
            PagePreflight(
                page_number=1,
                width=612,
                height=792,
                rotation=0,
                page_type="native_text",
            )
        ],
    )


def parse_with_fake_provider(tmp_path: Path):
    preflight = make_preflight(tmp_path)
    summary = build_data_flow_summary(
        EngineConfig(provider=ProviderConfig(name="fake", public=False, last_approved=True)),
        preflight,
    )
    parser_result = run_parse_stage(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
    )
    return preflight, parser_result


def test_model_stage_writes_document_json(tmp_path: Path) -> None:
    preflight, parser_result = parse_with_fake_provider(tmp_path)

    document = run_model_stage(tmp_path / "task", preflight, parser_result)

    document_json = tmp_path / "task" / "intermediates" / "document.json"
    assert document_json.is_file()
    assert '"provider_name": "fake"' in document_json.read_text(encoding="utf-8")
    assert document.provider_name == "fake"


def test_model_stage_writes_content_markdown(tmp_path: Path) -> None:
    preflight, parser_result = parse_with_fake_provider(tmp_path)

    run_model_stage(tmp_path / "task", preflight, parser_result)

    content_md = tmp_path / "task" / "intermediates" / "content.md"
    assert content_md.is_file()
    assert "# Sample Contract" in content_md.read_text(encoding="utf-8")


def test_docx_stage_writes_result_docx(tmp_path: Path) -> None:
    preflight, parser_result = parse_with_fake_provider(tmp_path)
    document = run_model_stage(tmp_path / "task", preflight, parser_result)

    updated = run_docx_stage(tmp_path / "task", document)

    assert (tmp_path / "task" / "result.docx").is_file()
    assert (tmp_path / "task" / "result-v1.docx").is_file()
    assert updated.document_id == document.document_id


def test_docx_stage_merges_build_issues_into_document(tmp_path: Path) -> None:
    preflight, parser_result = parse_with_fake_provider(tmp_path)
    document = run_model_stage(tmp_path / "task", preflight, parser_result)

    updated = run_docx_stage(tmp_path / "task", document)

    assert any(issue.issue_type == "asset_missing" for issue in updated.issues)


def test_model_stage_uses_mineru_result_zip_when_present(tmp_path: Path) -> None:
    preflight = make_preflight(tmp_path)
    raw_dir = tmp_path / "task" / "intermediates" / "provider-raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "result.json").write_text(
        json.dumps({"state": "done", "full_zip_url": "https://example.test/result.zip"}),
        encoding="utf-8",
    )
    with ZipFile(raw_dir / "result.zip", "w") as zf:
        zf.writestr(
            "abc_content_list.json",
            json.dumps(
                [
                    {
                        "type": "text",
                        "text": "MinerU Title",
                        "text_level": 1,
                        "page_idx": 0,
                    }
                ]
            ),
        )

    class Result:
        provider_name = "mineru"
        raw_result_dir = raw_dir
        metadata = {}

    document = run_model_stage(tmp_path / "task", preflight, Result())

    assert document.provider_name == "mineru"
    assert document.pages[0].blocks[0].spans[0].current_text == "MinerU Title"


def test_model_stage_restores_original_page_numbers_from_subset_mapping(
    tmp_path: Path,
) -> None:
    preflight = PreflightResult(
        source_path=tmp_path / "source.pdf",
        file_sha256="c" * 64,
        encrypted=False,
        page_count=5,
        pages=[
            PagePreflight(
                page_number=index,
                width=612,
                height=792,
                rotation=0,
                page_type="scanned",
            )
            for index in range(1, 6)
        ],
    )
    raw_dir = tmp_path / "task" / "intermediates" / "provider-raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "result.json").write_text(
        json.dumps(
            {
                "provider": {"name": "recording"},
                "document": {
                    "pages": [
                        {
                            "page_number": 1,
                            "blocks": [{"type": "paragraph", "text": "Selected page"}],
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    parser_result = ParserJobResult(
        provider_name="recording",
        raw_result_dir=raw_dir,
        metadata={"task_to_original": {1: 5}},
    )

    document = run_model_stage(tmp_path / "task", preflight, parser_result)

    assert document.pages[0].page_number == 5
    assert document.pages[0].original_page_number == 5
    assert document.pages[0].task_page_number == 1
