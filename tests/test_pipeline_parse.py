from pathlib import Path

import pytest

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import PreflightResult
from greatocr.pipeline import SecurityApprovalRequired, run_parse_stage
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
