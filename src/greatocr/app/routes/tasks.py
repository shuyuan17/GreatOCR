from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from greatocr.app.schemas import (
    DefaultOutputDirResponse,
    NewTask,
    TaskRecord,
    TaskResultFileEntry,
    TaskResultSummary,
)
from greatocr.app.services.task_service import TaskService, TaskServiceError
from greatocr.ingest.preflight import InvalidPdfError, run_preflight
from greatocr.selection.page_ranges import PageRangeError, parse_page_ranges


router = APIRouter(prefix="/tasks", tags=["tasks"])

RESULT_FILES = {
    "result_docx": "result.docx",
    "quality_report_docx": "quality-report.docx",
    "translated_docx": "translated_result.docx",
}


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


class BatchDeleteRequest(BaseModel):
    task_ids: list[str] = Field(min_length=1)


def _service(request: Request) -> TaskService:
    service = getattr(request.app.state, "task_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "TASK_SERVICE_UNAVAILABLE",
                "message": "任务服务不可用，请检查后端状态",
            },
        )
    return service


ERROR_MESSAGES: dict[str, str] = {
    "SOURCE_FILE_NOT_FOUND": "源文件未找到，请确认文件未被移动或删除",
    "OUTPUT_DIR_NOT_FOUND": "指定的输出目录不存在",
    "OUTPUT_DIR_NOT_DIRECTORY": "指定的输出路径不是一个目录",
    "OUTPUT_DIR_NOT_WRITABLE": "输出目录不可写，请检查权限",
    "TASK_NOT_FOUND": "任务未找到，请刷新后重试",
    "ENCRYPTED_PDF_NOT_SUPPORTED": "暂不支持加密的 PDF 文件",
    "INVALID_THUMBNAIL_WINDOW": "缩略图页码范围无效",
    "PROVIDER_NOT_FOUND": "OCR Provider 未找到",
    "CREDENTIAL_NOT_CONFIGURED": "当前 Provider 未配置 API Key，请前往设置中完成配置",
    "INVALID_PAGE_SELECTION": "页码范围无效，请重新选择",
    "SENSITIVE_CONFIRMATION_REQUIRED": "敏感文件需要额外确认才能提交",
    "SENSITIVE_PROVIDER_NOT_ALLOWED": "当前任务使用的 Provider 不允许处理敏感文件",
    "TRANSLATION_PROVIDER_REQUIRED": "OCR + 翻译模式必须选择翻译 Provider",
    "TRANSLATION_PROVIDER_NOT_FOUND": "翻译 Provider 未找到",
    "TRANSLATION_CREDENTIAL_NOT_CONFIGURED": "翻译 Provider 未配置 API Key，请前往设置中完成配置",
    "INVALID_RETRY_PAGES": "指定的重试页数无效",
    "SENSITIVE_SOURCE_REATTACH_REQUIRED": "敏感文件需要重新关联源文件",
    "UPLOAD_DIR_NOT_CONFIGURED": "上传目录未配置，请联系系统管理员",
    "PAGE_RANGE_REQUIRES_PDF": "只有 PDF 文件支持页码范围",
    "INVALID_TRANSLATION_MODE": "当前仅支持 Page by Page 翻译模式",
    "RESULT_FILE_NOT_FOUND": "结果文件未找到，可能尚未生成或已被删除",
}


def _run(action):
    try:
        return action()
    except TaskServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": ERROR_MESSAGES.get(exc.code, exc.code),
            },
        ) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(payload: NewTask, request: Request) -> TaskRecord:
    return _run(lambda: _service(request).create(payload))


@router.get("")
def list_tasks(request: Request) -> list[TaskRecord]:
    return _service(request).list()


@router.get("/default-output-dir")
def default_output_dir(request: Request) -> DefaultOutputDirResponse:
    return DefaultOutputDirResponse(
        output_dir=str(_service(request).default_output_dir())
    )


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
    return [{"page_number": item.page_number, "path": str(item.path)} for item in items]


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
    task = _run(lambda: _service(request).retry_failed_pages(task_id, payload.pages))
    return {**task.model_dump(), "retry_pages": payload.pages}


@router.get("/{task_id}/versions")
def task_versions(task_id: str, request: Request) -> list[str]:
    return _run(lambda: _service(request).versions(task_id))


@router.post("/{task_id}/open-output")
def open_task_output(task_id: str, request: Request) -> dict[str, str]:
    _run(lambda: _service(request).open_output(task_id))
    return {"status": "ok"}


@router.delete("/{task_id}")
def delete_task(task_id: str, request: Request) -> dict[str, str]:
    _run(lambda: _service(request).delete(task_id))
    return {"status": "ok", "task_id": task_id}


@router.post("/batch-delete")
def batch_delete_tasks(payload: BatchDeleteRequest, request: Request) -> dict[str, str]:
    _run(lambda: _service(request).batch_delete(payload.task_ids))
    return {"status": "ok", "deleted": str(len(payload.task_ids))}


@router.get("/{task_id}/result-files")
def task_result_files(task_id: str, request: Request) -> TaskResultSummary:
    task = _run(lambda: _service(request).get(task_id))
    output_dir = Path(task.output_dir)
    files = {
        key: TaskResultFileEntry(
            key=key,
            filename=filename,
            exists=(output_dir / filename).is_file(),
            download_path=(
                f"/api/tasks/{task_id}/download/{filename}"
                if (output_dir / filename).is_file()
                else None
            ),
        )
        for key, filename in RESULT_FILES.items()
    }
    return TaskResultSummary(task=task, files=files)


@router.get("/{task_id}/download/{filename}")
def download_task_result(task_id: str, filename: str, request: Request) -> FileResponse:
    task = _run(lambda: _service(request).get(task_id))
    if filename not in RESULT_FILES.values():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESULT_FILE_NOT_FOUND",
                "message": ERROR_MESSAGES["RESULT_FILE_NOT_FOUND"],
            },
        )
    target = Path(task.output_dir) / filename
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESULT_FILE_NOT_FOUND",
                "message": ERROR_MESSAGES["RESULT_FILE_NOT_FOUND"],
            },
        )
    return FileResponse(target, filename=filename)


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
    provider_profile_id: str = Form("mineru-default"),
    pages: str = Form(""),
    output_dir: str = Form(""),
    approved_fallback_ids: str = Form(""),
    processing_mode: str = Form("ocr"),
    ocr_provider_profile_id: str = Form(""),
    translation_provider_profile_id: str = Form(""),
    target_language: str = Form(""),
    translation_mode: str = Form(""),
) -> UploadResult:
    upload_dir: Path | None = getattr(request.app.state, "upload_dir", None)
    if upload_dir is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_DIR_NOT_CONFIGURED",
                "message": ERROR_MESSAGES["UPLOAD_DIR_NOT_CONFIGURED"],
            },
        )

    filename = Path(file.filename or "upload").name or "upload"
    file_id = uuid.uuid4().hex
    save_dir = upload_dir / file_id
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

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
                detail={
                    "code": "PAGE_RANGE_REQUIRES_PDF",
                    "message": ERROR_MESSAGES["PAGE_RANGE_REQUIRES_PDF"],
                },
            ) from exc
        try:
            parsed_pages = parse_page_ranges(pages, preflight.page_count).pages
        except PageRangeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PAGE_RANGE", "message": str(exc)},
            ) from exc

    if not parsed_pages:
        try:
            if preflight is None:
                preflight = run_preflight(save_path)
            if not preflight.encrypted:
                parsed_pages = list(range(1, preflight.page_count + 1))
        except InvalidPdfError:
            pass
        except Exception:
            pass

    parsed_fallback: list[str] = []
    if approved_fallback_ids and approved_fallback_ids.strip():
        parsed_fallback = [item.strip() for item in approved_fallback_ids.split(",") if item.strip()]

    parsed_mode = processing_mode.strip() if processing_mode else "ocr"
    if parsed_mode not in {"ocr", "translation"}:
        parsed_mode = "ocr"
    parsed_ocr_provider = ocr_provider_profile_id.strip() or None
    parsed_translation_provider = translation_provider_profile_id.strip() or None
    parsed_target_language = target_language.strip() or None
    raw_translation_mode = translation_mode.strip() or None

    try:
        parsed_translation_mode = NewTask.model_validate(
            {
                "source_path": str(save_path),
                "pages": parsed_pages,
                "provider_profile_id": provider_profile_id,
                "processing_mode": parsed_mode,
                "translation_mode": raw_translation_mode,
            }
        ).translation_mode
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_TRANSLATION_MODE",
                "message": ERROR_MESSAGES["INVALID_TRANSLATION_MODE"],
            },
        ) from exc

    new_task = NewTask(
        source_path=str(save_path),
        sensitive=sensitive,
        pages=parsed_pages,
        provider_profile_id=provider_profile_id,
        output_dir=output_dir.strip() or None,
        approved_fallback_ids=parsed_fallback,
        processing_mode=parsed_mode,
        ocr_provider_profile_id=parsed_ocr_provider,
        translation_provider_profile_id=parsed_translation_provider,
        target_language=parsed_target_language,
        translation_mode=parsed_translation_mode,
    )
    task = _run(lambda: _service(request).create(new_task))

    return UploadResult(task=task, file_path=str(save_path), size_bytes=len(content))
