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
from greatocr.app.services.worker import SerialWorker
from tests.app.test_credentials import FakeKeyring


def make_pdf(path: Path, pages: int = 3) -> Path:
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
    credentials.set("mineru-default", "test-secret")
    database.save_provider(
        {
            "profile_id": "mineru-default",
            "display_name": "MinerU",
            "adapter_type": "mineru",
            "endpoint": "https://mineru.net",
            "public": True,
            "capabilities": {"tables": True, "images": True},
        }
    )
    opened: list[Path] = []
    service = TaskService(
        database,
        credentials,
        ThumbnailService(tmp_path / "thumbnails"),
        output_opener=opened.append,
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
    yield client, database, opened, tmp_path
    database.close()


def headers() -> dict[str, str]:
    return {"X-GreatOCR-Token": "session-token"}


def create_task(client: TestClient, source: Path, *, sensitive: bool) -> dict:
    response = client.post(
        "/api/tasks",
        headers=headers(),
        json={
            "source_path": str(source),
            "sensitive": sensitive,
            "pages": [1, 3],
            "provider_profile_id": "mineru-default",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_sensitive_public_task_cannot_start_without_exact_confirmation(api) -> None:
    client, _, _, tmp_path = api
    source = make_pdf(tmp_path / "sample.pdf")
    task = create_task(client, source, sensitive=True)

    missing = client.post(f"/api/tasks/{task['task_id']}/start", headers=headers())
    wrong = client.post(
        f"/api/tasks/{task['task_id']}/start",
        headers=headers(),
        json={
            "confirmation": {
                "confirmed": True,
                "provider_profile_id": "mineru-default",
                "source_file_name": "wrong.pdf",
            }
        },
    )

    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "SENSITIVE_CONFIRMATION_REQUIRED"
    assert wrong.status_code == 409

    started = client.post(
        f"/api/tasks/{task['task_id']}/start",
        headers=headers(),
        json={
            "confirmation": {
                "confirmed": True,
                "provider_profile_id": "mineru-default",
                "source_file_name": "sample.pdf",
            }
        },
    )
    assert started.status_code == 200
    assert started.json()["status"] == "pending"
    approval_path = Path(started.json()["output_dir"]) / "approval.json"
    assert approval_path.is_file()
    assert "test-secret" not in approval_path.read_text(encoding="utf-8")


def test_task_preflight_and_thumbnail_window(api) -> None:
    client, _, _, tmp_path = api
    task = create_task(client, make_pdf(tmp_path / "preview.pdf"), sensitive=False)

    preflight = client.post(
        f"/api/tasks/{task['task_id']}/preflight",
        headers=headers(),
    )
    thumbnails = client.get(
        f"/api/tasks/{task['task_id']}/thumbnails?start=2&count=2",
        headers=headers(),
    )

    assert preflight.status_code == 200
    assert preflight.json()["page_count"] == 3
    assert [item["page_number"] for item in thumbnails.json()] == [2, 3]


def test_task_controls_versions_and_open_output(api) -> None:
    client, database, opened, tmp_path = api
    task = create_task(client, make_pdf(tmp_path / "controls.pdf"), sensitive=False)
    task_id = task["task_id"]

    client.post(f"/api/tasks/{task_id}/start", headers=headers())
    database.update_task_status(task_id, "running")
    paused = client.post(f"/api/tasks/{task_id}/pause", headers=headers())
    checkpointed = SerialWorker(database).checkpoint(task_id)
    retried = client.post(
        f"/api/tasks/{task_id}/retry-failed-pages",
        headers=headers(),
        json={"pages": [3]},
    )
    output_dir = Path(database.get_task(task_id).output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result-v1.docx").write_bytes(b"test")
    versions = client.get(f"/api/tasks/{task_id}/versions", headers=headers())
    opened_response = client.post(
        f"/api/tasks/{task_id}/open-output",
        headers=headers(),
    )
    cancelled = client.post(f"/api/tasks/{task_id}/cancel", headers=headers())

    assert paused.json()["status"] == "running"
    assert paused.json()["requested_action"] == "pause"
    assert checkpointed.status == "paused"
    assert retried.json()["status"] == "pending"
    assert retried.json()["retry_pages"] == [3]
    assert versions.json() == ["result-v1.docx"]
    assert opened_response.json() == {"status": "ok"}
    assert opened == [output_dir]
    assert cancelled.json()["status"] == "cancelled"


def test_task_list_and_detail_do_not_expose_sensitive_source_path(api) -> None:
    client, _, _, tmp_path = api
    source = make_pdf(tmp_path / "client-secret.pdf")
    task = create_task(client, source, sensitive=True)

    detail = client.get(f"/api/tasks/{task['task_id']}", headers=headers())
    listed = client.get("/api/tasks", headers=headers())

    assert detail.json()["source_path"] is None
    assert listed.json()[0]["source_path"] is None
    assert "client-secret.pdf" not in detail.text


def test_upload_file_accepts_page_ranges(api) -> None:
    client, _, _, tmp_path = api
    source = make_pdf(tmp_path / "range-upload.pdf", pages=5)

    with source.open("rb") as stream:
        response = client.post(
            "/api/tasks/upload-file",
            headers=headers(),
            data={
                "provider_profile_id": "mineru-default",
                "pages": "1-3,5",
            },
            files={"file": ("range-upload.pdf", stream, "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json()["task"]["selected_pages"] == [1, 2, 3, 5]
