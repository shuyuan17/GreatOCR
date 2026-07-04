from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from greatocr.app.schemas import NewTask, TaskRecord
from greatocr.app.services.task_service import TaskService, TaskServiceError
from greatocr.ingest.preflight import InvalidPdfError, run_preflight
from greatocr.selection.page_ranges import PageRangeError, parse_page_ranges


router = APIRouter(prefix="/tasks", tags=["tasks"])


class StartConfirmation(BaseModel):
    model_config = ConfigDict(frozen=True)

    confirmed: bool
    provider_profile_id: str
    source_file_name: str


class StartRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    confirmation: StartConfirmation | None = None


class RetryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    pages: list[int] = Field(min_length=1)


def _service(request: Request) -> TaskService:
    service = getattr(request.app.state, "task_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "TASK_SERVICE_UNAVAILABLE"},
        )
    return service


def _run(action):
    try:
        return action()
    except TaskServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code},
        ) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(payload: NewTask, request: Request) -> TaskRecord:
    return _run(lambda: _service(request).create(payload))


@router.get("")
def list_tasks(request: Request) -> list[TaskRecord]:
    return _service(request).list()


@router.get("/{task_id}")
def get_task(task_id: str, request: Request) -> TaskRecord:
    return _run(lambda: _service(request).get(task_id))


@router.post("/{task_id}/preflight")
def preflight_task(task_id: str, request: Request) -> dict[str, Any]:
    result = _run(lambda: _service(request).preflight(task_id))
    return {
        "page_count": result.page_count,
        "encrypted": result.encrypted,
        "pages": [page.model_dump() for page in result.pages],
    }


@router.get("/{task_id}/thumbnails")
def task_thumbnails(
    task_id: str,
    request: Request,
    start: int = 1,
    count: int = 10,
) -> list[dict[str, Any]]:
    items = _run(
        lambda: _service(request).render_thumbnails(
            task_id,
            start=start,
            count=count,
        )
    )
    return [
        {"page_number": item.page_number, "path": str(item.path)} for item in items
    ]


@router.post("/{task_id}/start")
def start_task(
    task_id: str,
    request: Request,
    payload: StartRequest | None = None,
) -> TaskRecord:
    confirmation = (
        payload.confirmation.model_dump()
        if payload is not None and payload.confirmation is not None
        else None
    )
    return _run(lambda: _service(request).start(task_id, confirmation))


@router.post("/{task_id}/pause")
def pause_task(task_id: str, request: Request) -> TaskRecord:
    return _run(lambda: _service(request).pause(task_id))


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, request: Request) -> TaskRecord:
    return _run(lambda: _service(request).cancel(task_id))


@router.post("/{task_id}/retry-failed-pages")
def retry_failed_pages(
    task_id: str,
    payload: RetryRequest,
    request: Request,
) -> dict[str, Any]:
    task = _run(
        lambda: _service(request).retry_failed_pages(task_id, payload.pages)
    )
    return {**task.model_dump(), "retry_pages": payload.pages}


@router.get("/{task_id}/versions")
def task_versions(task_id: str, request: Request) -> list[str]:
    return _run(lambda: _service(request).versions(task_id))


@router.post("/{task_id}/open-output")
def open_task_output(task_id: str, request: Request) -> dict[str, str]:
    _run(lambda: _service(request).open_output(task_id))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# 文件上传 + 创建任务（合并为一步，适合 Web 前端使用）
# ---------------------------------------------------------------------------

class UploadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    task: TaskRecord
    file_path: str
    size_bytes: int


@router.post("/upload-file", status_code=status.HTTP_201_CREATED)
async def upload_and_create_task(
    request: Request,
    file: UploadFile = File(...),
    sensitive: bool = Form(False),
    provider_profile_id: str = Form("fake-default"),
    pages: str = Form(""),
    approved_fallback_ids: str = Form(""),
) -> UploadResult:
    """接收文件上传，保存到 uploads 目录后直接创建任务。

    参数：
      file:                  上传的文件（PDF 或图片）
      sensitive:             是否敏感任务（默认 false）
      provider_profile_id:   OCR provider ID（默认 fake-default）
      pages:                 逗号分隔的页码，如 "1,2,3"；留空表示全部页面
      approved_fallback_ids: 逗号分隔的 fallback provider ID 列表

    返回：
      task:      已创建的任务记录（状态为 paused）
      file_path: 服务器上保存的文件路径
      size_bytes: 文件大小
    """
    upload_dir: Path | None = getattr(request.app.state, "upload_dir", None)
    if upload_dir is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "UPLOAD_DIR_NOT_CONFIGURED"},
        )

    # 校验文件名，防止路径穿越
    filename = file.filename or "upload"
    safe_name = Path(filename).name
    if not safe_name:
        safe_name = "upload"

    # 生成唯一子目录保存文件
    file_id = uuid.uuid4().hex
    save_dir = upload_dir / file_id
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / safe_name

    content = await file.read()
    save_path.write_bytes(content)

    preflight = None
    parsed_pages: list[int] = []
    if pages and pages.strip():
        try:
            preflight = run_preflight(save_path)
        except InvalidPdfError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "PAGE_RANGE_REQUIRES_PDF"},
            ) from exc
        try:
            parsed_pages = parse_page_ranges(pages, preflight.page_count).pages
        except PageRangeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PAGE_RANGE", "message": str(exc)},
            ) from exc

    # 如果未指定页面，尝试预检获取总页数（仅 PDF）
    if not parsed_pages:
        try:
            if preflight is None:
                preflight = run_preflight(save_path)
            if not preflight.encrypted:
                parsed_pages = list(range(1, preflight.page_count + 1))
        except InvalidPdfError:
            # 不是有效 PDF（可能是图片），不设页面限制
            pass
        except Exception:
            # 其他预检失败不阻塞上传
            pass

    parsed_fallback: list[str] = []
    if approved_fallback_ids and approved_fallback_ids.strip():
        for f in approved_fallback_ids.split(","):
            f = f.strip()
            if f:
                parsed_fallback.append(f)

    # 通过已有 TaskService 创建任务
    new_task = NewTask(
        source_path=str(save_path),
        sensitive=sensitive,
        pages=parsed_pages,
        provider_profile_id=provider_profile_id,
        approved_fallback_ids=parsed_fallback,
    )
    task = _run(lambda: _service(request).create(new_task))

    return UploadResult(
        task=task,
        file_path=str(save_path),
        size_bytes=len(content),
    )
