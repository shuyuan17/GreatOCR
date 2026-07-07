from __future__ import annotations

from typing import Any, Mapping

import httpx
from pydantic import SecretStr

from greatocr.providers.mineru import MinerUConfig, probe_mineru_connection


class ProviderConnectionError(RuntimeError):
    """Raised when a provider connection probe cannot complete successfully."""


def _probe_openai_compatible_connection(
    profile: Mapping[str, Any],
    secret: SecretStr,
    *,
    client: httpx.Client | None = None,
) -> None:
    endpoint = str(profile.get("endpoint") or "").strip()
    model = str(profile.get("model") or "").strip()
    if not endpoint:
        raise ProviderConnectionError("Provider endpoint is not configured.")
    if not model:
        raise ProviderConnectionError("Provider model is not configured.")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "请只回复：连接成功",
            }
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {secret.get_secret_value()}",
        "Content-Type": "application/json",
    }

    transport_client = client or httpx.Client(timeout=30.0)
    owns_client = client is None
    try:
        response = transport_client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ProviderConnectionError(
            f"Connection test failed with status {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise ProviderConnectionError("Connection test request failed.") from exc
    finally:
        if owns_client:
            transport_client.close()


def probe_provider_connection(
    profile: Mapping[str, Any],
    secret: SecretStr,
    *,
    client: httpx.Client | None = None,
) -> None:
    adapter_type = profile.get("adapter_type")
    if adapter_type == "mineru":
        config = MinerUConfig(
            base_url=profile.get("endpoint") or "https://mineru.net",
            api_key=secret,
        )
        probe_mineru_connection(config, client=client)
        return
    if adapter_type in {"openai-compatible", "deepseek"}:
        _probe_openai_compatible_connection(profile, secret, client=client)
        return

    raise ValueError(f"Unsupported provider adapter: {adapter_type}")
