from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from greatocr.app.db import TaskDatabase
from greatocr.app.main import create_app
from greatocr.app.services.credentials import CredentialService
from greatocr.app.services.task_service import TaskService
from greatocr.app.services.thumbnails import ThumbnailService
from tests.app.test_credentials import FakeKeyring


def make_pdf(path: Path, pages: int = 1) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


@pytest.fixture
def api(tmp_path: Path):
    database = TaskDatabase(tmp_path / "greatocr.db")
    keyring = FakeKeyring()
    credentials = CredentialService(keyring)
    credentials.set("ocr-allowed", "ocr-secret")
    credentials.set("ocr-blocked", "ocr-secret")
    credentials.set("translation-allowed", "translation-secret")
    credentials.set("translation-blocked", "translation-secret")

    database.save_provider(
        {
            "profile_id": "ocr-allowed",
            "display_name": "OCR Allowed",
            "adapter_type": "mineru",
            "endpoint": "https://ocr.allowed.test",
            "public": True,
            "sensitive_allowed": True,
            "capabilities": {"tables": True, "images": True},
        }
    )
    database.save_provider(
        {
            "profile_id": "ocr-blocked",
            "display_name": "OCR Blocked",
            "adapter_type": "mineru",
            "endpoint": "https://ocr.blocked.test",
            "public": False,
            "sensitive_allowed": False,
            "capabilities": {"tables": True, "images": True},
        }
    )
    database.save_provider(
        {
            "profile_id": "translation-allowed",
            "display_name": "Zhipu GLM",
            "adapter_type": "openai-compatible",
            "endpoint": "https://translation.allowed.test/chat/completions",
            "model": "glm-4-plus",
            "public": True,
            "sensitive_allowed": True,
            "capabilities": {"translation": True, "text_processing": True},
        }
    )
    database.save_provider(
        {
            "profile_id": "translation-blocked",
            "display_name": "Translation Blocked",
            "adapter_type": "openai-compatible",
            "endpoint": "https://translation.blocked.test/chat/completions",
            "model": "blocked-model",
            "public": True,
            "sensitive_allowed": False,
            "capabilities": {"translation": True, "text_processing": True},
        }
    )

    service = TaskService(
        database,
        credentials,
        ThumbnailService(tmp_path / "thumbnails"),
    )
    app = create_app(
        session_token="session-token",
        allowed_origin="http://127.0.0.1:4173",
        database=database,
        credential_service=credentials,
        task_service=service,
        upload_dir=tmp_path / "uploads",
    )
    client = TestClient(app)
    yield client, database, tmp_path
    database.close()


def headers() -> dict[str, str]:
    return {"X-GreatOCR-Token": "session-token"}


def test_upload_file_normalizes_page_by_page_translation_mode(api) -> None:
    client, _, tmp_path = api
    source = make_pdf(tmp_path / "page-by-page.pdf")

    with source.open("rb") as stream:
        response = client.post(
            "/api/tasks/upload-file",
            headers=headers(),
            data={
                "provider_profile_id": "ocr-allowed",
                "processing_mode": "translation",
                "ocr_provider_profile_id": "ocr-allowed",
                "translation_provider_profile_id": "translation-allowed",
                "target_language": "Chinese",
                "translation_mode": "Page by Page",
            },
            files={"file": ("page-by-page.pdf", stream, "application/pdf")},
        )

    assert response.status_code == 201
    task = response.json()["task"]
    assert task["processing_mode"] == "translation"
    assert task["translation_mode"] == "page"


def test_upload_file_rejects_unsupported_translation_mode(api) -> None:
    client, _, tmp_path = api
    source = make_pdf(tmp_path / "unsupported-mode.pdf")

    with source.open("rb") as stream:
        response = client.post(
            "/api/tasks/upload-file",
            headers=headers(),
            data={
                "provider_profile_id": "ocr-allowed",
                "processing_mode": "translation",
                "ocr_provider_profile_id": "ocr-allowed",
                "translation_provider_profile_id": "translation-allowed",
                "target_language": "Chinese",
                "translation_mode": "Document",
            },
            files={"file": ("unsupported-mode.pdf", stream, "application/pdf")},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_TRANSLATION_MODE"


def test_sensitive_task_starts_when_every_used_provider_allows_sensitive_files(api) -> None:
    client, _, tmp_path = api
    source = make_pdf(tmp_path / "sensitive-allowed.pdf")

    with source.open("rb") as stream:
        created = client.post(
            "/api/tasks/upload-file",
            headers=headers(),
            data={
                "sensitive": "true",
                "provider_profile_id": "ocr-allowed",
                "processing_mode": "translation",
                "ocr_provider_profile_id": "ocr-allowed",
                "translation_provider_profile_id": "translation-allowed",
                "target_language": "Chinese",
                "translation_mode": "page",
            },
            files={"file": ("sensitive-allowed.pdf", stream, "application/pdf")},
        )

    assert created.status_code == 201
    task_id = created.json()["task"]["task_id"]

    started = client.post(f"/api/tasks/{task_id}/start", headers=headers())

    assert started.status_code == 200
    assert started.json()["status"] == "pending"


def test_sensitive_task_is_rejected_when_any_used_provider_blocks_sensitive_files(api) -> None:
    client, _, tmp_path = api
    source = make_pdf(tmp_path / "sensitive-blocked.pdf")

    with source.open("rb") as stream:
        created = client.post(
            "/api/tasks/upload-file",
            headers=headers(),
            data={
                "sensitive": "true",
                "provider_profile_id": "ocr-allowed",
                "processing_mode": "translation",
                "ocr_provider_profile_id": "ocr-allowed",
                "translation_provider_profile_id": "translation-blocked",
                "target_language": "Chinese",
                "translation_mode": "page",
            },
            files={"file": ("sensitive-blocked.pdf", stream, "application/pdf")},
        )

    assert created.status_code == 201
    task_id = created.json()["task"]["task_id"]

    started = client.post(f"/api/tasks/{task_id}/start", headers=headers())

    assert started.status_code == 409
    assert started.json()["detail"]["code"] == "SENSITIVE_PROVIDER_NOT_ALLOWED"
