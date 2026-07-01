from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import PreflightResult
from greatocr.pipeline import SecurityApprovalRequired, run_parse_stage
from greatocr.providers.base import DocumentParser, ParserJobResult, ProviderCapabilities
from greatocr.providers.fake import FakeDocumentParser
from greatocr.providers.mineru import MinerUConfig, MinerUDocumentParser
from greatocr.security import SecurityMode, build_data_flow_summary


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


def make_preflight(tmp_path: Path) -> PreflightResult:
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    return PreflightResult(
        source_path=source_pdf,
        file_sha256="a" * 64,
        encrypted=False,
        page_count=1,
        pages=[],
    )


def test_parse_stage_with_fake_provider_writes_provider_raw(tmp_path: Path) -> None:
    preflight = make_preflight(tmp_path)
    summary = build_data_flow_summary(
        EngineConfig(
            provider=ProviderConfig(
                name="fake",
                public=False,
                last_approved=True,
            )
        ),
        preflight,
    )

    result = run_parse_stage(
        tmp_path / "task",
        preflight,
        FakeDocumentParser(FIXTURE),
        summary,
    )

    assert result.raw_result_dir == tmp_path / "task" / "intermediates" / "provider-raw"
    assert (result.raw_result_dir / "result.json").is_file()


def test_sensitive_mode_blocks_public_provider_without_approval(tmp_path: Path) -> None:
    preflight = make_preflight(tmp_path)
    summary = build_data_flow_summary(
        EngineConfig(
            security_mode=SecurityMode.SENSITIVE,
            provider=ProviderConfig(
                name="mineru",
                endpoint="https://mineru.example.test",
                public=True,
                last_approved=False,
            ),
        ),
        preflight,
    )
    parser = MinerUDocumentParser(
        MinerUConfig(base_url="https://mineru.example.test", api_key="test-key"),
        upload_confirmed=True,
    )

    with pytest.raises(SecurityApprovalRequired, match="not approved"):
        run_parse_stage(tmp_path / "task", preflight, parser, summary)


class RecordingParser(DocumentParser):
    def __init__(self) -> None:
        self.received_page_count = 0

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=True,
            tables=True,
            formulas=False,
            languages=["auto"],
            data_residency="local-fixture",
        )

    def parse_document(self, source_pdf: Path, raw_result_dir: Path) -> ParserJobResult:
        self.received_page_count = len(PdfReader(source_pdf).pages)
        raw_result_dir.mkdir(parents=True, exist_ok=True)
        (raw_result_dir / "result.json").write_text(
            '{"provider":{"name":"recording"},"document":{"pages":[]}}',
            encoding="utf-8",
        )
        return ParserJobResult(
            provider_name="recording",
            raw_result_dir=raw_result_dir,
            metadata={},
        )


def test_parse_stage_sends_only_selected_pages_to_provider(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(5):
        writer.add_blank_page(width=612, height=792)
    with source.open("wb") as stream:
        writer.write(stream)
    preflight = PreflightResult(
        source_path=source,
        file_sha256="b" * 64,
        encrypted=False,
        page_count=5,
        pages=[],
    )
    summary = build_data_flow_summary(
        EngineConfig(
            provider=ProviderConfig(
                name="recording",
                public=False,
                last_approved=True,
            )
        ),
        preflight,
    )
    parser = RecordingParser()

    result = run_parse_stage(
        tmp_path / "task",
        preflight,
        parser,
        summary,
        selected_pages=[2, 5],
    )

    assert parser.received_page_count == 2
    assert result.metadata["task_to_original"] == {1: 2, 2: 5}
