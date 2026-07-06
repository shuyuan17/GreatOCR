from __future__ import annotations

from pathlib import Path

import httpx
from pydantic import SecretStr

from greatocr.app.db import TaskDatabase
from greatocr.app.release_bootstrap import ensure_release_defaults
from greatocr.app.services.provider_connections import probe_provider_connection


def test_release_defaults_create_mineru_only(tmp_path: Path) -> None:
    database = TaskDatabase(tmp_path / "greatocr.db")
    try:
        ensure_release_defaults(database, data_dir=tmp_path / "runtime-data")

        mineru = database.get_provider("mineru-default")

        assert mineru is not None
        assert mineru["display_name"] == "MinerU"
        assert mineru["adapter_type"] == "mineru"
        assert mineru["endpoint"] == "https://mineru.net"
        assert database.get_provider("fake-default") is None
        assert database.get_preferences()["output_default_dir"] == str(
            tmp_path / "runtime-data" / "exports"
        )
    finally:
        database.close()


def test_release_connection_test_uses_mineru_probe() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example.test/api-upload/probe"],
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    probe_provider_connection(
        {
            "profile_id": "mineru-default",
            "display_name": "MinerU",
            "adapter_type": "mineru",
            "endpoint": "https://mineru.example.test",
            "public": True,
            "capabilities": {},
            "approved_fallback_ids": [],
        },
        SecretStr("probe-secret"),
        client=client,
    )

    assert [request.url.path for request in requests] == ["/api/v4/file-urls/batch"]
    assert requests[0].headers["Authorization"] == "Bearer probe-secret"
