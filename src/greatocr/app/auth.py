from __future__ import annotations

from secrets import compare_digest

from fastapi import HTTPException, Request, status


def require_local_session(request: Request) -> None:
    supplied_token = request.headers.get("X-GreatOCR-Token")
    expected_token = request.app.state.session_token
    if not supplied_token or not compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SESSION_TOKEN"},
        )

    origin = request.headers.get("Origin")
    if origin is not None and not _origin_matches_allowed_loopback(
        origin,
        request.app.state.allowed_origin,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ORIGIN_NOT_ALLOWED"},
        )


def _origin_matches_allowed_loopback(origin: str, allowed_origin: str) -> bool:
    return origin.rstrip("/") == allowed_origin.rstrip("/")
