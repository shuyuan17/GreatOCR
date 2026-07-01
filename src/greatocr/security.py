from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from greatocr.ingest.preflight import PreflightResult


class SecurityMode(StrEnum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"


class RetentionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    keep_intermediates: bool
    keep_page_cache: bool
    keep_final_outputs: bool = True


class DataFlowSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_mode: SecurityMode
    source_file_name: str
    page_count: int
    provider_name: str
    provider_endpoint: str | None
    provider_public: bool
    external_upload_allowed: bool
    requires_confirmation: bool
    retention_policy: RetentionPolicy
    approved_profile_ids: list[str] = Field(default_factory=list)
    confirmed_at: datetime | None = None


def build_data_flow_summary(config, preflight: PreflightResult) -> DataFlowSummary:
    sensitive = config.security_mode == SecurityMode.SENSITIVE
    provider_public = bool(config.provider.public)
    external_upload_allowed = bool(config.provider.last_approved) and not (
        sensitive and provider_public
    )

    retention_policy = RetentionPolicy(
        keep_intermediates=not sensitive,
        keep_page_cache=False,
    )

    return DataFlowSummary(
        security_mode=config.security_mode,
        source_file_name=preflight.source_path.name,
        page_count=preflight.page_count,
        provider_name=config.provider.name,
        provider_endpoint=config.provider.endpoint,
        provider_public=provider_public,
        external_upload_allowed=external_upload_allowed,
        requires_confirmation=sensitive or not external_upload_allowed,
        retention_policy=retention_policy,
    )


def approve_data_flow(
    summary: DataFlowSummary,
    approved_profile_ids: list[str],
) -> DataFlowSummary:
    if not approved_profile_ids:
        raise ValueError("at least one provider profile must be approved")
    return summary.model_copy(
        update={
            "approved_profile_ids": list(dict.fromkeys(approved_profile_ids)),
            "confirmed_at": datetime.now(timezone.utc),
            "external_upload_allowed": True,
            "requires_confirmation": False,
        }
    )
