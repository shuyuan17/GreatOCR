from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Mapping

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from greatocr.providers.base import DocumentParser, ParserJobResult, ProviderCapabilities


class ProviderConfigurationError(RuntimeError):
    """Raised when provider configuration is incomplete or invalid."""


class ProviderPermissionError(PermissionError):
    """Raised when a provider action requires explicit user approval."""


class ProviderJobFailed(RuntimeError):
    """Raised when a provider job fails or cannot complete."""


class MinerUConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "https://mineru.net"
    api_key: SecretStr

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "MinerUConfig":
        source = env if env is not None else os.environ
        base_url = source.get("MINERU_BASE_URL", "https://mineru.net")
        api_key = source.get("MINERU_API_KEY")

        missing = []
        if not api_key:
            missing.append("MINERU_API_KEY")
        if missing:
            raise ProviderConfigurationError(
                "Missing MinerU configuration: " + ", ".join(missing)
            )

        return cls(base_url=base_url, api_key=api_key)

    @classmethod
    def from_key_file(cls, path: Path, *, base_url: str = "https://mineru.net") -> "MinerUConfig":
        token = path.read_text(encoding="utf-8").strip()
        if token.startswith("Bearer "):
            token = token.removeprefix("Bearer ").strip()
        if not token:
            raise ProviderConfigurationError("MinerU API key file is empty")
        return cls(base_url=base_url, api_key=token)


class MinerUDocumentParser(DocumentParser):
    def __init__(
        self,
        config: MinerUConfig,
        *,
        client: httpx.Client | None = None,
        upload_confirmed: bool = False,
        max_retries: int = 2,
        max_polls: int = 10,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=30)
        self.upload_confirmed = upload_confirmed
        self.max_retries = max_retries
        self.max_polls = max_polls
        self.poll_interval_seconds = poll_interval_seconds

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=True,
            layout=True,
            tables=True,
            images=True,
            formulas=True,
            languages=["auto"],
            data_residency="provider-defined",
        )

    def parse_document(self, source_pdf: Path, raw_result_dir: Path) -> ParserJobResult:
        if not self.upload_confirmed:
            raise ProviderPermissionError(
                "MinerU upload requires explicit confirmation before sending files."
            )
        if not source_pdf.exists():
            raise FileNotFoundError(f"input file does not exist: {source_pdf}")

        raw_result_dir.mkdir(parents=True, exist_ok=True)
        batch_payload = self._create_upload_batch(source_pdf)
        self._write_json(raw_result_dir / "batch.json", batch_payload)

        upload_url = batch_payload["file_urls"][0]
        self._upload_file(upload_url, source_pdf)
        self._write_json(raw_result_dir / "upload.json", {"uploaded": source_pdf.name})

        final_status = self._poll_batch(batch_payload["batch_id"], source_pdf.name)
        self._write_json(raw_result_dir / "status.json", final_status)
        self._write_json(raw_result_dir / "result.json", final_status)

        full_zip_url = final_status.get("full_zip_url")
        if full_zip_url:
            zip_response = self.client.get(full_zip_url)
            zip_response.raise_for_status()
            (raw_result_dir / "result.zip").write_bytes(zip_response.content)

        return ParserJobResult(
            provider_name="mineru",
            raw_result_dir=raw_result_dir,
            metadata={"batch_id": batch_payload["batch_id"]},
        )

    def _create_upload_batch(self, source_pdf: Path) -> dict:
        response = self._request(
            "POST",
            "/api/v4/file-urls/batch",
            json={"files": [{"name": source_pdf.name, "data_id": source_pdf.name}]},
        )
        payload = response.json()
        self._ensure_success_code(payload)
        data = payload.get("data", {})
        if "batch_id" not in data or not data.get("file_urls"):
            raise ProviderJobFailed("MinerU batch response missing batch_id or file_urls")
        return data

    def _upload_file(self, upload_url: str, source_pdf: Path) -> None:
        response = self.client.put(upload_url, content=source_pdf.read_bytes())
        response.raise_for_status()

    def _poll_batch(self, batch_id: str, file_name: str) -> dict:
        for _ in range(self.max_polls):
            response = self._request("GET", f"/api/v4/extract-results/batch/{batch_id}")
            payload = response.json()
            self._ensure_success_code(payload)
            for result in payload.get("data", {}).get("extract_result", []):
                if result.get("file_name") != file_name:
                    continue
                state = result.get("state")
                if state == "done":
                    return result
                if state == "failed":
                    raise ProviderJobFailed(result.get("err_msg", "MinerU job failed"))
            if self.poll_interval_seconds:
                time.sleep(self.poll_interval_seconds)
        raise ProviderJobFailed("MinerU job did not finish before poll limit")

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        attempts = self.max_retries + 1
        last_response: httpx.Response | None = None
        for _ in range(attempts):
            response = self.client.request(
                method,
                self._url(path),
                headers=self._headers(),
                **kwargs,
            )
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response
            last_response = response

        assert last_response is not None
        raise ProviderJobFailed(
            f"MinerU request failed after retries with HTTP {last_response.status_code}"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
        }

    def _url(self, path: str) -> str:
        return self.config.base_url.rstrip("/") + path

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _ensure_success_code(payload: dict) -> None:
        if payload.get("code", 0) != 0:
            raise ProviderJobFailed(payload.get("msg", "MinerU request failed"))
