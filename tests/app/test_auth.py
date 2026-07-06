from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from greatocr.app.main import create_app, validate_bind_host


@pytest.fixture
def session_token() -> str:
    return "current-session-token"


@pytest.fixture
def allowed_origin() -> str:
    return "http://127.0.0.1:4173"


@pytest.fixture
def client(session_token: str, allowed_origin: str) -> TestClient:
    return TestClient(create_app(session_token=session_token, allowed_origin=allowed_origin))


def test_health_accepts_requests_without_session_token(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_non_health_api_rejects_missing_or_wrong_session_token(client: TestClient) -> None:
    assert client.get("/api/providers").status_code == 401
    assert (
        client.get(
            "/api/providers",
            headers={"X-GreatOCR-Token": "wrong"},
        ).status_code
        == 401
    )


def test_api_accepts_current_session_token(
    client: TestClient,
    session_token: str,
) -> None:
    response = client.get(
        "/api/health",
        headers={"X-GreatOCR-Token": session_token},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_rejects_foreign_browser_origin(
    client: TestClient,
    session_token: str,
) -> None:
    response = client.get(
        "/api/providers",
        headers={
            "X-GreatOCR-Token": session_token,
            "Origin": "https://attacker.example",
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize("origin", ["http://127.0.0.1:4173", "http://localhost:4173"])
def test_api_accepts_loopback_browser_origin_aliases(
    client: TestClient,
    session_token: str,
    origin: str,
) -> None:
    response = client.get(
        "/api/providers",
        headers={
            "X-GreatOCR-Token": session_token,
            "Origin": origin,
        },
    )

    assert response.status_code != 401


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.5"])
def test_launcher_rejects_non_loopback_bind_hosts(host: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        validate_bind_host(host)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_launcher_accepts_loopback_bind_hosts(host: str) -> None:
    assert validate_bind_host(host) == host
