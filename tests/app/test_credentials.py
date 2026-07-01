from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from greatocr.app.db import TaskDatabase
from greatocr.app.main import create_app
from greatocr.app.schemas import NewTask
from greatocr.app.services.credentials import (
    CredentialNotConfigured,
    CredentialService,
)


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        del self.values[(service, username)]


@pytest.fixture
def fake_keyring() -> FakeKeyring:
    return FakeKeyring()


def test_credential_service_masks_and_deletes_secret(
    fake_keyring: FakeKeyring,
) -> None:
    service = CredentialService(fake_keyring, service_name="GreatOCR")
    service.set("mineru-default", "abcdef123456")

    assert service.status("mineru-default").model_dump() == {
        "configured": True,
        "masked": "********3456",
    }
    assert service.resolve("mineru-default").get_secret_value() == "abcdef123456"

    service.delete("mineru-default")
    assert service.status("mineru-default").configured is False
    with pytest.raises(CredentialNotConfigured):
        service.resolve("mineru-default")


def test_credential_service_rejects_blank_secret(fake_keyring: FakeKeyring) -> None:
    service = CredentialService(fake_keyring)

    with pytest.raises(ValueError, match="cannot be empty"):
        service.set("mineru-default", "   ")


@pytest.fixture
def provider_payload() -> dict[str, object]:
    return {
        "profile_id": "mineru-default",
        "display_name": "MinerU",
        "adapter_type": "mineru",
        "endpoint": "https://mineru.net",
        "public": True,
        "capabilities": {"tables": True, "images": True},
    }


def make_client(
    tmp_path: Path,
    fake_keyring: FakeKeyring,
    *,
    tester=None,
) -> tuple[TestClient, TaskDatabase]:
    database = TaskDatabase(tmp_path / "greatocr.db")
    credentials = CredentialService(fake_keyring)
    app = create_app(
        session_token="session-token",
        allowed_origin="http://127.0.0.1:4173",
        database=database,
        credential_service=credentials,
        provider_connection_tester=tester,
    )
    return TestClient(app), database


def auth_headers(**extra: str) -> dict[str, str]:
    return {"X-GreatOCR-Token": "session-token", **extra}


def test_provider_api_returns_masked_status_and_never_secret(
    tmp_path: Path,
    fake_keyring: FakeKeyring,
    provider_payload: dict[str, object],
) -> None:
    client, database = make_client(tmp_path, fake_keyring)
    try:
        response = client.post(
            "/api/providers",
            json=provider_payload,
            headers=auth_headers(**{"X-GreatOCR-Provider-Key": "top-secret-1234"}),
        )
        listed = client.get("/api/providers", headers=auth_headers())

        assert response.status_code == 200
        assert listed.status_code == 200
        assert listed.json()[0]["credential"] == {
            "configured": True,
            "masked": "********1234",
        }
        assert "top-secret-1234" not in listed.text
        assert "top-secret-1234" not in database.raw_database_text()
    finally:
        database.close()


def test_provider_connection_uses_resolved_secret_without_returning_it(
    tmp_path: Path,
    fake_keyring: FakeKeyring,
    provider_payload: dict[str, object],
) -> None:
    received: list[str] = []

    def tester(profile: dict[str, object], secret) -> None:
        assert profile["profile_id"] == "mineru-default"
        received.append(secret.get_secret_value())

    client, database = make_client(tmp_path, fake_keyring, tester=tester)
    try:
        client.post(
            "/api/providers",
            json=provider_payload,
            headers=auth_headers(**{"X-GreatOCR-Provider-Key": "connection-secret"}),
        )
        response = client.post(
            "/api/providers/mineru-default/test-connection",
            headers=auth_headers(),
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert received == ["connection-secret"]
        assert "connection-secret" not in response.text
    finally:
        database.close()


def test_provider_connection_failure_returns_fixed_error_code(
    tmp_path: Path,
    fake_keyring: FakeKeyring,
    provider_payload: dict[str, object],
) -> None:
    def failing_tester(profile, secret) -> None:
        raise RuntimeError("provider leaked connection-secret")

    client, database = make_client(tmp_path, fake_keyring, tester=failing_tester)
    try:
        client.post(
            "/api/providers",
            json=provider_payload,
            headers=auth_headers(**{"X-GreatOCR-Provider-Key": "connection-secret"}),
        )
        response = client.post(
            "/api/providers/mineru-default/test-connection",
            headers=auth_headers(),
        )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "PROVIDER_CONNECTION_FAILED"
        assert "connection-secret" not in response.text
        assert "provider leaked" not in response.text
    finally:
        database.close()


def test_provider_capability_test_and_delete(
    tmp_path: Path,
    fake_keyring: FakeKeyring,
    provider_payload: dict[str, object],
) -> None:
    client, database = make_client(tmp_path, fake_keyring)
    try:
        client.post(
            "/api/providers",
            json=provider_payload,
            headers=auth_headers(**{"X-GreatOCR-Provider-Key": "temporary-secret"}),
        )
        capabilities = client.post(
            "/api/providers/mineru-default/test-capabilities",
            headers=auth_headers(),
        )
        deleted = client.delete(
            "/api/providers/mineru-default",
            headers=auth_headers(),
        )

        assert capabilities.status_code == 200
        assert capabilities.json()["capabilities"] == {
            "tables": True,
            "images": True,
        }
        assert deleted.status_code == 204
        assert fake_keyring.values == {}
        assert client.get("/api/providers", headers=auth_headers()).json() == []
    finally:
        database.close()


def test_provider_delete_is_blocked_while_running_task_uses_it(
    tmp_path: Path,
    fake_keyring: FakeKeyring,
    provider_payload: dict[str, object],
) -> None:
    client, database = make_client(tmp_path, fake_keyring)
    try:
        client.post(
            "/api/providers",
            json=provider_payload,
            headers=auth_headers(),
        )
        task = database.create_task(
            NewTask(source_path="C:/docs/sample.pdf", pages=[1])
        )
        database.update_task_status(task.task_id, "running")

        response = client.delete(
            "/api/providers/mineru-default",
            headers=auth_headers(),
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "PROVIDER_IN_USE"
    finally:
        database.close()
