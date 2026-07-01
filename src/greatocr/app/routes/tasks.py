from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from greatocr.app.schemas import NewTask, TaskRecord
from greatocr.app.services.task_service import TaskService, TaskServiceError


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
