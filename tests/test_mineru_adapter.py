from pathlib import Path

import httpx
import pytest

from greatocr.providers.base import ProviderCapabilities
from greatocr.providers.mineru import (
    MinerUConfig,
    MinerUDocumentParser,
    ProviderConfigurationError,
    ProviderJobFailed,
    ProviderPermissionError,
)


def make_config() -> MinerUConfig:
    return MinerUConfig(base_url="https://mineru.example.test", api_key="test-key")


def test_from_env_requires_api_key() -> None:
    with pytest.raises(ProviderConfigurationError, match="MINERU_API_KEY"):
        MinerUConfig.from_env({})


def test_configuration_error_does_not_leak_secret() -> None:
    config = MinerUConfig.from_env({"MINERU_API_KEY": "super-secret-value"})

    assert "super-secret-value" not in repr(config)


def test_from_key_file_reads_token_without_requiring_env(tmp_path: Path) -> None:
    key_file = tmp_path / "mineru-key.txt"
    key_file.write_text("file-secret-token\n", encoding="utf-8")

    config = MinerUConfig.from_key_file(key_file)

    assert config.api_key.get_secret_value() == "file-secret-token"
    assert config.base_url == "https://mineru.net"


def test_mineru_capabilities_do_not_require_network() -> None:
    parser = MinerUDocumentParser(make_config(), upload_confirmed=False)

    capabilities = parser.capabilities()

    assert isinstance(capabilities, ProviderCapabilities)
    assert capabilities.native_pdf is True
    assert capabilities.scanned_pdf is True
    assert capabilities.coordinates is True
    assert capabilities.layout is True
    assert capabilities.tables is True
    assert capabilities.images is True
    assert capabilities.formulas is True


def test_parse_requires_explicit_upload_confirmation(tmp_path: Path) -> None:
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    parser = MinerUDocumentParser(make_config(), upload_confirmed=False)

    with pytest.raises(ProviderPermissionError, match="explicit confirmation"):
        parser.parse_document(source_pdf, tmp_path / "raw")


def test_parse_uploads_submits_polls_and_downloads_result(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.startswith("/api/v4"):
            assert request.headers["Authorization"] == "Bearer test-key"
        if request.url.path == "/api/v4/file-urls/batch":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "ok",
                    "data": {
                        "batch_id": "batch-1",
                        "file_urls": ["https://upload.example.test/api-upload/sample"],
                    },
                },
            )
        if request.url.host == "upload.example.test":
            assert "Authorization" not in request.headers
            return httpx.Response(200)
        if request.url.path == "/api/v4/extract-results/batch/batch-1":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "batch_id": "batch-1",
                        "extract_result": [
                            {
                                "file_name": "sample.pdf",
                                "state": "done",
                                "full_zip_url": "https://cdn.example.test/result.zip",
                                "data_id": "sample.pdf",
                            }
                        ],
                    },
                },
            )
        if request.url.host == "cdn.example.test":
            return httpx.Response(200, content=b"zip-bytes")
        return httpx.Response(404)

    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    parser = MinerUDocumentParser(make_config(), client=client, upload_confirmed=True)

    result = parser.parse_document(source_pdf, tmp_path / "raw")

    assert result.provider_name == "mineru"
    assert (result.raw_result_dir / "upload.json").is_file()
    assert (result.raw_result_dir / "batch.json").is_file()
    assert (result.raw_result_dir / "result.json").is_file()
    assert (result.raw_result_dir / "result.zip").is_file()
    assert result.metadata["batch_id"] == "batch-1"
    assert [request.url.path for request in requests] == [
        "/api/v4/file-urls/batch",
        "/api-upload/sample",
        "/api/v4/extract-results/batch/batch-1",
        "/result.zip",
    ]


def test_failed_job_status_raises_provider_job_failed(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v4/file-urls/batch":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "batch_id": "batch-1",
                        "file_urls": ["https://upload.example.test/api-upload/sample"],
                    },
                },
            )
        if request.url.host == "upload.example.test":
            return httpx.Response(200)
        if request.url.path == "/api/v4/extract-results/batch/batch-1":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "batch_id": "batch-1",
                        "extract_result": [
                            {
                                "file_name": "sample.pdf",
                                "state": "failed",
                                "err_msg": "OCR failed",
                            }
                        ],
                    },
                },
            )
        return httpx.Response(404)

    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    parser = MinerUDocumentParser(
        make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        upload_confirmed=True,
    )

    with pytest.raises(ProviderJobFailed, match="OCR failed"):
        parser.parse_document(source_pdf, tmp_path / "raw")


def test_temporary_429_is_retried(tmp_path: Path) -> None:
    upload_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal upload_attempts
        if request.url.path == "/api/v4/file-urls/batch":
            upload_attempts += 1
            if upload_attempts == 1:
                return httpx.Response(429, json={"message": "rate limited"})
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "batch_id": "batch-1",
                        "file_urls": ["https://upload.example.test/api-upload/sample"],
                    },
                },
            )
        if request.url.host == "upload.example.test":
            return httpx.Response(200)
        if request.url.path == "/api/v4/extract-results/batch/batch-1":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "batch_id": "batch-1",
                        "extract_result": [
                            {
                                "file_name": "sample.pdf",
                                "state": "done",
                                "full_zip_url": "https://cdn.example.test/result.zip",
                            }
                        ],
                    },
                },
            )
        if request.url.host == "cdn.example.test":
            return httpx.Response(200, content=b"zip-bytes")
        return httpx.Response(404)

    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    parser = MinerUDocumentParser(
        make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        upload_confirmed=True,
        max_retries=1,
    )

    parser.parse_document(source_pdf, tmp_path / "raw")

    assert upload_attempts == 2


def test_running_batch_status_polls_until_done(tmp_path: Path) -> None:
    poll_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal poll_count
        if request.url.path == "/api/v4/file-urls/batch":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "batch_id": "batch-1",
                        "file_urls": ["https://upload.example.test/api-upload/sample"],
                    },
                },
            )
        if request.url.host == "upload.example.test":
            return httpx.Response(200)
        if request.url.path == "/api/v4/extract-results/batch/batch-1":
            poll_count += 1
            state = "running" if poll_count == 1 else "done"
            payload = {
                "file_name": "sample.pdf",
                "state": state,
                "full_zip_url": "https://cdn.example.test/result.zip",
            }
            return httpx.Response(
                200,
                json={"code": 0, "data": {"batch_id": "batch-1", "extract_result": [payload]}},
            )
        if request.url.host == "cdn.example.test":
            return httpx.Response(200, content=b"zip-bytes")
        return httpx.Response(404)

    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.7 sample")
    parser = MinerUDocumentParser(
        make_config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        upload_confirmed=True,
        poll_interval_seconds=0,
    )

    parser.parse_document(source_pdf, tmp_path / "raw")

    assert poll_count == 2
