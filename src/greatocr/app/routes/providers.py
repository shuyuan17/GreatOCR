from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from greatocr.app.db import TaskDatabase
from greatocr.app.services.credentials import (
    CredentialNotConfigured,
    CredentialService,
    CredentialStatus,
)


router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderProfileInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    display_name: str
    adapter_type: Literal["mineru", "generic_vision", "fake"]
    endpoint: str | None = None
    public: bool = True
    capabilities: dict[str, Any] = Field(default_factory=dict)
    approved_fallback_ids: list[str] = Field(default_factory=list)


class ProviderView(ProviderProfileInput):
    credential: CredentialStatus


def _services(request: Request) -> tuple[TaskDatabase, CredentialService]:
    database = getattr(request.app.state, "database", None)
    credentials = getattr(request.app.state, "credential_service", None)
    if database is None or credentials is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "PROVIDER_SERVICE_UNAVAILABLE"},
        )
    return database, credentials


def _view(profile: dict[str, Any], credentials: CredentialService) -> ProviderView:
    return ProviderView(**profile, credential=credentials.status(profile["profile_id"]))


@router.get("")
def list_providers(request: Request) -> list[ProviderView]:
    database, credentials = _services(request)
    return [_view(profile, credentials) for profile in database.list_providers()]


@router.post("")
def save_provider(
    profile: ProviderProfileInput,
    request: Request,
    provider_key: str | None = Header(
        default=None,
        alias="X-GreatOCR-Provider-Key",
    ),
) -> ProviderView:
    database, credentials = _services(request)
    database.save_provider(profile)
    if provider_key is not None:
        credentials.set(profile.profile_id, provider_key)
    stored = database.get_provider(profile.profile_id)
    assert stored is not None
    return _view(stored, credentials)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(profile_id: str, request: Request) -> Response:
    database, credentials = _services(request)
    if database.provider_in_use(profile_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PROVIDER_IN_USE"},
        )
    if database.get_provider(profile_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROVIDER_NOT_FOUND"},
        )
    database.delete_provider(profile_id)
    credentials.delete(profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{profile_id}/test-connection")
def test_connection(profile_id: str, request: Request) -> dict[str, str]:
    database, credentials = _services(request)
    profile = database.get_provider(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROVIDER_NOT_FOUND"},
        )
    try:
        secret = credentials.resolve(profile_id)
    except CredentialNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CREDENTIAL_NOT_CONFIGURED"},
        ) from exc

    tester: Callable[[dict[str, Any], SecretStr], None] | None = getattr(
        request.app.state,
        "provider_connection_tester",
        None,
    )
    if tester is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "CONNECTION_TEST_UNAVAILABLE"},
        )
    try:
        tester(profile, secret)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "PROVIDER_CONNECTION_FAILED"},
        ) from exc
    return {"status": "ok"}


@router.post("/{profile_id}/test-capabilities")
def test_capabilities(profile_id: str, request: Request) -> dict[str, Any]:
    database, _ = _services(request)
    profile = database.get_provider(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROVIDER_NOT_FOUND"},
        )
    return {
        "profile_id": profile_id,
        "capabilities": profile["capabilities"],
    }
