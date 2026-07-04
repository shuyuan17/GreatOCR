from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from greatocr.app.auth import require_local_session
from greatocr.app.routes.preferences import router as preferences_router
from greatocr.app.routes.providers import router as providers_router
from greatocr.app.routes.tasks import router as tasks_router


api_router = APIRouter()
api_router.include_router(preferences_router)
api_router.include_router(providers_router)
api_router.include_router(tasks_router)


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
    task_service=None,
    upload_dir: str | Path | None = None,
) -> FastAPI:
    if not session_token:
        raise ValueError("session token cannot be empty")
    if not allowed_origin:
        raise ValueError("allowed origin cannot be empty")

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    # 全局异常处理器：避免暴露 Python 栈追踪
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        # 如果是已知 HTTPException（由路由逻辑主动抛出的），直接透传
        if isinstance(exc, StarletteHTTPException):
            # 给没有 message 的异常补充默认消息
            detail = exc.detail
            if isinstance(detail, dict) and "message" not in detail:
                detail["message"] = "请求处理出错"
            return JSONResponse(
                status_code=exc.status_code,
                content=detail,
            )
        # 未知异常 → 返回 500，不暴露内部细节
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务器内部错误，请查看后端日志获取详细信息"},
        )

    app.state.session_token = session_token
    app.state.allowed_origin = allowed_origin.rstrip("/")
    app.state.database = database
    app.state.credential_service = credential_service
    app.state.provider_connection_tester = provider_connection_tester
    app.state.task_service = task_service
    app.state.upload_dir = Path(upload_dir) if upload_dir else None
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
