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
        deepseek = database.get_provider("deepseek-default")
        zhipu = database.get_provider("zhipu-glm-default")

        assert mineru is not None
        assert mineru["display_name"] == "MinerU"
        assert mineru["adapter_type"] == "mineru"
        assert mineru["endpoint"] == "https://mineru.net"
        assert deepseek is not None
        assert deepseek["display_name"] == "DeepSeek 翻译"
        assert zhipu is not None
        assert zhipu["display_name"] == "智谱 GLM"
        assert zhipu["adapter_type"] == "openai-compatible"
        assert zhipu["endpoint"] == "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        assert zhipu["model"] == "glm-4-plus"
        assert zhipu["public"] is True
        assert zhipu["capabilities"]["translation"] is True
        assert zhipu["capabilities"]["text_processing"] is True
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


def test_release_connection_test_uses_openai_compatible_chat_probe() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "连接成功"},
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    probe_provider_connection(
        {
            "profile_id": "zhipu-glm-default",
            "display_name": "智谱 GLM",
            "adapter_type": "openai-compatible",
            "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "model": "glm-4-plus",
            "public": True,
            "capabilities": {
                "translation": True,
                "text_processing": True,
            },
            "approved_fallback_ids": [],
        },
        SecretStr("glm-secret"),
        client=client,
    )

    assert [str(request.url) for request in requests] == [
        "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    ]
    assert requests[0].headers["Authorization"] == "Bearer glm-secret"
    assert requests[0].headers["Content-Type"] == "application/json"
    assert requests[0].read().decode("utf-8") == (
        '{"model":"glm-4-plus","messages":[{"role":"user","content":"请只回复：连接成功"}],"temperature":0}'
    )
