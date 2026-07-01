from __future__ import annotations

from ipaddress import ip_address

from fastapi import APIRouter, Depends, FastAPI

from greatocr.app.auth import require_local_session
from greatocr.app.routes.providers import router as providers_router


api_router = APIRouter()
api_router.include_router(providers_router)


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(
    session_token: str,
    allowed_origin: str,
    *,
    database=None,
    credential_service=None,
    provider_connection_tester=None,
) -> FastAPI:
    if not session_token:
        raise ValueError("session token cannot be empty")
    if not allowed_origin:
        raise ValueError("allowed origin cannot be empty")

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.session_token = session_token
    app.state.allowed_origin = allowed_origin.rstrip("/")
    app.state.database = database
    app.state.credential_service = credential_service
    app.state.provider_connection_tester = provider_connection_tester
    app.include_router(
        api_router,
        prefix="/api",
        dependencies=[Depends(require_local_session)],
    )
    return app


def validate_bind_host(host: str) -> str:
    if host == "localhost":
        return host
    try:
        address = ip_address(host)
    except ValueError as exc:
        raise ValueError("GreatOCR may bind only to a loopback host") from exc
    if not address.is_loopback:
        raise ValueError("GreatOCR may bind only to a loopback host")
    return host
