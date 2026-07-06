from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from greatocr.app.db import TaskDatabase
from greatocr.app.schemas import NewTask, TaskRecord
from greatocr.app.services.credentials import CredentialService
from greatocr.app.services.thumbnails import Thumbnail, ThumbnailService
from greatocr.ingest.preflight import PreflightResult, run_preflight


class TaskServiceError(RuntimeError):
    def __init__(self, code: str, *, status_code: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class TaskService:
    def __init__(
        self,
        database: TaskDatabase,
        credentials: CredentialService,
        thumbnails: ThumbnailService,
        *,
        output_opener: Callable[[Path], None] | None = None,
    ) -> None:
        self.database = database
        self.credentials = credentials
        self.thumbnails = thumbnails
        self.output_opener = output_opener or self._open_output_directory
        self._runtime_source_paths: dict[str, Path] = {}

    def create(self, request: NewTask) -> TaskRecord:
        source = Path(request.source_path)
        if not source.is_file():
            raise TaskServiceError("SOURCE_FILE_NOT_FOUND", status_code=404)
        output_dir = self.resolve_output_dir(request.output_dir)
        request = request.model_copy(
            update={"output_dir": str(output_dir / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))}
        )
        record = self.database.create_task(request)
        self.database.update_task_status(record.task_id, "paused")
        self._runtime_source_paths[record.task_id] = source
        updated = self.database.get_task(record.task_id)
        assert updated is not None
        return updated

    def default_output_dir(self) -> Path:
        path = self.database.path.parent / "exports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_output_dir(self, raw_output_dir: str | None) -> Path:
        output_root = Path(raw_output_dir) if raw_output_dir else self.default_output_dir()
        if not output_root.exists():
            raise TaskServiceError("OUTPUT_DIR_NOT_FOUND", status_code=422)
        if not output_root.is_dir():
            raise TaskServiceError("OUTPUT_DIR_NOT_DIRECTORY", status_code=422)
        probe = output_root / ".greatocr-write-test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise TaskServiceError("OUTPUT_DIR_NOT_WRITABLE", status_code=422) from exc
        return output_root

    def get(self, task_id: str) -> TaskRecord:
        task = self.database.get_task(task_id)
        if task is None:
            raise TaskServiceError("TASK_NOT_FOUND", status_code=404)
        return task

    def list(self) -> list[TaskRecord]:
        return self.database.list_tasks()

    def preflight(self, task_id: str) -> PreflightResult:
        result = run_preflight(self._source_path(task_id))
        if result.encrypted:
            raise TaskServiceError("ENCRYPTED_PDF_NOT_SUPPORTED")
        return result

    def render_thumbnails(
        self,
        task_id: str,
        *,
        start: int,
        count: int,
    ) -> list[Thumbnail]:
        result = self.preflight(task_id)
        if start < 1 or count < 1:
            raise TaskServiceError("INVALID_THUMBNAIL_WINDOW", status_code=422)
        end = min(result.page_count, start + count - 1)
        return self.thumbnails.render(
            self._source_path(task_id),
            pages=range(start, end + 1),
        )

    def start(
        self,
        task_id: str,
        confirmation: dict[str, Any] | None,
    ) -> TaskRecord:
        task = self.get(task_id)
        provider = self.database.get_provider(task.provider_profile_id)
        if provider is None:
            raise TaskServiceError("PROVIDER_NOT_FOUND", status_code=404)
        if not self.credentials.status(task.provider_profile_id).configured:
            raise TaskServiceError("CREDENTIAL_NOT_CONFIGURED")
        preflight = self.preflight(task_id)
        if not task.selected_pages or any(
            page > preflight.page_count for page in task.selected_pages
        ):
            raise TaskServiceError("INVALID_PAGE_SELECTION", status_code=422)

        if task.sensitive and provider["public"]:
            source_name = self._source_path(task_id).name
            expected = {
                "confirmed": True,
                "provider_profile_id": task.provider_profile_id,
                "source_file_name": source_name,
            }
            if confirmation != expected:
                raise TaskServiceError("SENSITIVE_CONFIRMATION_REQUIRED")
            self._write_approval(task, expected)

        self.database.update_task_status(task_id, "pending")
        return self.get(task_id)

    def pause(self, task_id: str) -> TaskRecord:
        task = self.get(task_id)
        if task.status == "running":
            self.database.request_task_action(task_id, "pause")
        else:
            self.database.update_task_status(task_id, "paused")
        return self.get(task_id)

    def cancel(self, task_id: str) -> TaskRecord:
        task = self.get(task_id)
        if task.status == "running":
            self.database.request_task_action(task_id, "cancel")
        else:
            self.database.update_task_status(task_id, "cancelled")
        return self.get(task_id)

    def retry_failed_pages(self, task_id: str, pages: list[int]) -> TaskRecord:
        task = self.get(task_id)
        if not pages or any(page not in task.selected_pages for page in pages):
            raise TaskServiceError("INVALID_RETRY_PAGES", status_code=422)
        output_dir = Path(task.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "retry-request.json").write_text(
            json.dumps({"pages": pages}, indent=2),
            encoding="utf-8",
        )
        self.database.update_task_status(task_id, "pending")
        return self.get(task_id)

    def versions(self, task_id: str) -> list[str]:
        task = self.get(task_id)
        return sorted(path.name for path in Path(task.output_dir).glob("result-v*.docx"))

    def open_output(self, task_id: str) -> None:
        task = self.get(task_id)
        output_dir = Path(task.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_opener(output_dir)

    def delete(self, task_id: str) -> None:
        """删除任务记录。不会删除输出文件或原始文件。"""
        self.get(task_id)  # 确认任务存在（不存在则抛 404）
        self.database.delete_task(task_id)

    def batch_delete(self, task_ids: list[str]) -> None:
        """批量删除任务记录。不会删除输出文件或原始文件。"""
        for task_id in task_ids:
            try:
                self.database.delete_task(task_id)
            except KeyError:
                pass  # 跳过已删除或不存在的任务

    def _source_path(self, task_id: str) -> Path:
        task = self.get(task_id)
        source = self._runtime_source_paths.get(task_id)
        if source is None and task.source_path is not None:
            source = Path(task.source_path)
        if source is None:
            raise TaskServiceError("SENSITIVE_SOURCE_REATTACH_REQUIRED")
        return source

    @staticmethod
    def _write_approval(task: TaskRecord, confirmation: dict[str, Any]) -> None:
        output_dir = Path(task.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            **confirmation,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        (output_dir / "approval.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _open_output_directory(path: Path) -> None:
        os.startfile(path)  # type: ignore[attr-defined]
