from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Literal

import fitz
import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

from greatocr.providers.base import DocumentParser, ParserJobResult, ProviderCapabilities
from greatocr.providers.profiles import ProviderProfile


class ExperimentalProviderOutputError(RuntimeError):
    """Raised when an experimental model response violates the strict contract."""


class GenericVisionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint: str
    api_key: SecretStr
    model_name: str


class VisionBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[
        "title",
        "paragraph",
        "list",
        "table",
        "image",
        "header",
        "footer",
        "page_number",
    ]
    text: str = ""
    bbox: tuple[float, float, float, float]
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_bbox(self) -> "VisionBlock":
        x0, y0, x1, y1 = self.bbox
        if not all(0 <= value <= 1 for value in self.bbox):
            raise ValueError("bbox coordinates must be normalized to 0..1")
        if x0 > x1 or y0 > y1:
            raise ValueError("bbox coordinates must be ordered")
        return self


class VisionPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    blocks: list[VisionBlock]


class GenericVisionDocumentParser(DocumentParser):
    def __init__(
        self,
        config: GenericVisionConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=60)

    @classmethod
    def from_profile(
        cls,
        profile: ProviderProfile,
        *,
        api_key: str,
        client: httpx.Client | None = None,
    ) -> "GenericVisionDocumentParser":
        if not profile.model_name:
            raise ValueError(f"generic vision profile requires model_name: {profile.profile_id}")
        return cls(
            GenericVisionConfig(
                endpoint=profile.endpoint,
                api_key=api_key,
                model_name=profile.model_name,
            ),
            client=client,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=True,
            layout=True,
            tables=True,
            images=True,
            formulas=False,
            languages=["auto"],
            data_residency="provider-defined",
        )

    def parse_document(self, source_pdf: Path, raw_result_dir: Path) -> ParserJobResult:
        if not source_pdf.exists():
            raise FileNotFoundError(f"input file does not exist: {source_pdf}")
        raw_result_dir.mkdir(parents=True, exist_ok=True)

        pages: list[dict] = []
        with fitz.open(source_pdf) as pdf:
            for page_index, page in enumerate(pdf, start=1):
                png_bytes = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("png")
                envelope = self._request_page(page_index, png_bytes)
                self._write_json(
                    raw_result_dir / f"response-page-{page_index:04d}.json",
                    envelope,
                )
                vision_page = self._parse_page(envelope, expected_page=page_index)
                page_payload = vision_page.model_dump(mode="json")
                for block in page_payload["blocks"]:
                    block["bbox_unit"] = "normalized"
                pages.append(page_payload)

        result_payload = {
            "provider": {
                "name": "generic_vision",
                "model_name": self.config.model_name,
            },
            "document": {"pages": pages},
        }
        self._write_json(raw_result_dir / "result.json", result_payload)
        return ParserJobResult(
            provider_name="generic_vision",
            raw_result_dir=raw_result_dir,
            metadata={"model_name": self.config.model_name, "page_count": len(pages)},
        )

    def _request_page(self, page_number: int, png_bytes: bytes) -> dict:
        image = base64.b64encode(png_bytes).decode("ascii")
        response = self.client.post(
            self.config.endpoint,
            headers={
                "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model_name,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Extract document structure without rewriting text. Return only JSON "
                            "matching the supplied schema. Bounding boxes must use 0..1 coordinates."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Extract PDF page {page_number}."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image}"},
                            },
                        ],
                    },
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "greatocr_vision_page",
                        "strict": True,
                        "schema": VisionPage.model_json_schema(),
                    },
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ExperimentalProviderOutputError("model response envelope is invalid")
        return payload

    @staticmethod
    def _parse_page(envelope: dict, *, expected_page: int) -> VisionPage:
        try:
            content = envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ExperimentalProviderOutputError(
                "model response envelope is missing message content"
            ) from exc
        if not isinstance(content, str):
            raise ExperimentalProviderOutputError("model response content must be a JSON string")
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ExperimentalProviderOutputError("model response is not valid JSON") from exc
        try:
            page = VisionPage.model_validate(decoded)
        except ValidationError as exc:
            raise ExperimentalProviderOutputError(
                "model response failed the GreatOCR page schema"
            ) from exc
        if page.page_number != expected_page:
            raise ExperimentalProviderOutputError("model response page number does not match request")
        return page

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
