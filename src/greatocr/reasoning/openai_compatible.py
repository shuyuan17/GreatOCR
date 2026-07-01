from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr, TypeAdapter, ValidationError

from greatocr.model.document import Document
from greatocr.reasoning.base import CorrectionProposal, TextReasoner


class ReasonerOutputError(RuntimeError):
    """Raised when a text reasoner returns an invalid proposal list."""


class OpenAIReasonerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint: str
    api_key: SecretStr
    model_name: str


class OpenAICompatibleReasoner(TextReasoner):
    def __init__(
        self,
        config: OpenAIReasonerConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=30)

    def propose(self, document: Document) -> list[CorrectionProposal]:
        candidates = [
            {
                "span_id": span.span_id,
                "current_text": span.current_text[:500],
                "confidence": span.confidence,
                "is_critical": span.is_critical,
            }
            for page in document.pages
            for block in page.blocks
            for span in block.spans
            if span.confidence < 0.9
        ]
        if not candidates:
            return []

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
                            "Propose conservative OCR spacing and line-break corrections. "
                            "Do not rewrite meaning or change critical values. Return only JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(candidates, ensure_ascii=False),
                    },
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "greatocr_corrections",
                        "strict": True,
                        "schema": {
                            "type": "array",
                            "items": CorrectionProposal.model_json_schema(),
                        },
                    },
                },
            },
        )
        response.raise_for_status()
        try:
            envelope = response.json()
            content = envelope["choices"][0]["message"]["content"]
            decoded = json.loads(content)
            return TypeAdapter(list[CorrectionProposal]).validate_python(decoded)
        except (ValueError, KeyError, IndexError, TypeError, ValidationError) as exc:
            raise ReasonerOutputError(
                "text reasoner response failed the correction schema"
            ) from exc
