from pathlib import Path

from greatocr.config import EngineConfig, ProviderConfig
from greatocr.ingest.preflight import PreflightResult
from greatocr.security import SecurityMode, approve_data_flow, build_data_flow_summary


def make_preflight() -> PreflightResult:
    return PreflightResult(
        source_path=Path("sample.pdf"),
        file_sha256="a" * 64,
        encrypted=False,
        page_count=3,
        pages=[],
    )


def test_normal_mode_allows_last_approved_provider() -> None:
    config = EngineConfig(
        provider=ProviderConfig(
            name="mineru",
            endpoint="https://api.example.test",
            api_key="secret-key",
            public=True,
            last_approved=True,
        )
    )

    summary = build_data_flow_summary(config, make_preflight())

    assert summary.security_mode == SecurityMode.NORMAL
    assert summary.provider_name == "mineru"
    assert summary.external_upload_allowed is True
    assert summary.requires_confirmation is False


def test_sensitive_mode_blocks_public_provider_by_default() -> None:
    config = EngineConfig(
        security_mode=SecurityMode.SENSITIVE,
        provider=ProviderConfig(
            name="mineru",
            endpoint="https://api.example.test",
            api_key="secret-key",
            public=True,
            last_approved=True,
        ),
    )

    summary = build_data_flow_summary(config, make_preflight())

    assert summary.external_upload_allowed is False
    assert summary.requires_confirmation is True
    assert summary.retention_policy.keep_intermediates is False


def test_data_flow_summary_never_contains_api_key() -> None:
    config = EngineConfig(
        provider=ProviderConfig(
            name="mineru",
            endpoint="https://api.example.test",
            api_key="secret-key",
            public=True,
            last_approved=True,
        )
    )

    summary = build_data_flow_summary(config, make_preflight())

    assert "secret-key" not in summary.model_dump_json()


def test_sensitive_confirmation_records_only_approved_profile_ids() -> None:
    config = EngineConfig(
        security_mode=SecurityMode.SENSITIVE,
        provider=ProviderConfig(name="mineru", public=True, last_approved=True),
    )
    summary = build_data_flow_summary(config, make_preflight())

    approved = approve_data_flow(summary, ["mineru-default", "private-backup"])

    assert approved.external_upload_allowed is True
    assert approved.requires_confirmation is False
    assert approved.approved_profile_ids == ["mineru-default", "private-backup"]
    assert approved.confirmed_at is not None
