import json
from pathlib import Path

import httpx
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from greatocr.providers.generic_vision import (
    ExperimentalProviderOutputError,
    GenericVisionConfig,
    GenericVisionDocumentParser,
)


def sample_pdf(path: Path) -> Path:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.drawString(72, 720, "Vision adapter sample")
    pdf.save()
    return path


def valid_page_payload() -> dict:
    return {
        "page_number": 1,
        "blocks": [
            {
                "type": "paragraph",
                "text": "Recognized text",
                "bbox": [0.1, 0.1, 0.8, 0.2],
                "confidence": 0.94,
            }
        ],
    }


def chat_response(content: object) -> dict:
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


def make_parser(handler) -> GenericVisionDocumentParser:
    return GenericVisionDocumentParser(
        GenericVisionConfig(
            endpoint="https://vision.example.test/v1/chat/completions",
            api_key="test-secret",
            model_name="vision-test",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_generic_vision_rejects_non_json_model_output(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        )

    parser = make_parser(handler)

    with pytest.raises(ExperimentalProviderOutputError, match="valid JSON"):
        parser.parse_document(sample_pdf(tmp_path / "sample.pdf"), tmp_path / "raw")


def test_generic_vision_writes_schema_valid_result(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert payload["model"] == "vision-test"
        assert payload["response_format"]["type"] == "json_schema"
        image_url = payload["messages"][1]["content"][1]["image_url"]["url"]
        assert image_url.startswith("data:image/png;base64,")
        return httpx.Response(200, json=chat_response(valid_page_payload()))

    parser = make_parser(handler)

    result = parser.parse_document(
        sample_pdf(tmp_path / "sample.pdf"),
        tmp_path / "raw",
    )
    normalized = json.loads((result.raw_result_dir / "result.json").read_text(encoding="utf-8"))

    assert len(requests) == 1
    assert normalized["provider"]["name"] == "generic_vision"
    assert normalized["document"]["pages"][0]["blocks"][0]["text"] == "Recognized text"
    assert normalized["document"]["pages"][0]["blocks"][0]["bbox_unit"] == "normalized"
    assert (result.raw_result_dir / "response-page-0001.json").is_file()


def test_generic_vision_rejects_invalid_bbox_without_guessing(tmp_path: Path) -> None:
    payload = valid_page_payload()
    payload["blocks"][0]["bbox"] = [0.8, 0.1, 0.2, 0.3]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=chat_response(payload))

    with pytest.raises(ExperimentalProviderOutputError, match="schema"):
        make_parser(handler).parse_document(
            sample_pdf(tmp_path / "sample.pdf"),
            tmp_path / "raw",
        )


def test_generic_vision_error_never_contains_api_key(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    with pytest.raises(ExperimentalProviderOutputError) as captured:
        make_parser(handler).parse_document(
            sample_pdf(tmp_path / "sample.pdf"),
            tmp_path / "raw",
        )

    assert "test-secret" not in str(captured.value)
