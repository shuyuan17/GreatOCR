from __future__ import annotations

from typing import Any, Mapping

import httpx
from pydantic import SecretStr

from greatocr.providers.mineru import MinerUConfig, probe_mineru_connection


def probe_provider_connection(
    profile: Mapping[str, Any],
    secret: SecretStr,
    *,
    client: httpx.Client | None = None,
) -> None:
    adapter_type = profile.get("adapter_type")
    if adapter_type != "mineru":
        raise ValueError(f"Unsupported provider adapter: {adapter_type}")

    config = MinerUConfig(
        base_url=profile.get("endpoint") or "https://mineru.net",
        api_key=secret,
    )
    probe_mineru_connection(config, client=client)
