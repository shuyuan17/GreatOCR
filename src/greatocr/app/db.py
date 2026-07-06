from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path, PurePath
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4

from pydantic import BaseModel

from greatocr.app.schemas import (
    NewTask,
    RequestedTaskAction,
    TaskRecord,
    TaskStatus,
)


SCHEMA_VERSION = 4


class TaskDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create_task(self, request: NewTask) -> TaskRecord:
        task_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        display_name = (
            "敏感任务 " + created_at[:19].replace("T", " ")
            if request.sensitive
            else PurePath(request.source_path).name
        )
        source_path = None if request.sensitive else request.source_path
        output_dir = request.output_dir or str(self.path.parent / "tasks" / task_id)
        # OCR Provider：优先使用新字段，缺省回退到 provider_profile_id（向后兼容）。
        ocr_provider_profile_id = (
            request.ocr_provider_profile_id or request.provider_profile_id
        )
        record = TaskRecord(
            task_id=task_id,
            display_name=display_name,
            source_path=source_path,
            sensitive=request.sensitive,
            selected_pages=request.pages,
            provider_profile_id=request.provider_profile_id,
            approved_fallback_ids=request.approved_fallback_ids,
            status="pending",
            output_dir=output_dir,
            created_at=created_at,
            processing_mode=request.processing_mode,
            ocr_provider_profile_id=ocr_provider_profile_id,
            translation_provider_profile_id=request.translation_provider_profile_id,
            target_language=request.target_language,
            translation_mode=request.translation_mode,
        )
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO tasks (
                    task_id, display_name, source_path, sensitive, selected_pages,
                    provider_profile_id, approved_fallback_ids, status, output_dir,
                    quality_rating, requested_action, created_at, completed_at,
                    processing_mode, ocr_provider_profile_id,
                    translation_provider_profile_id, target_language, translation_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.task_id,
                    record.display_name,
                    record.source_path,
                    int(record.sensitive),
                    json.dumps(record.selected_pages),
                    record.provider_profile_id,
                    json.dumps(record.approved_fallback_ids),
                    record.status,
                    record.output_dir,
                    record.quality_rating,
                    record.requested_action,
                    record.created_at,
                    None,  # completed_at
                    record.processing_mode,
                    record.ocr_provider_profile_id,
                    record.translation_provider_profile_id,
                    record.target_language,
                    record.translation_mode,
                ),
            )
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._task_from_row(row) if row is not None else None

    def list_tasks(self) -> list[TaskRecord]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC, rowid DESC"
            ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE tasks SET status = ? WHERE task_id = ?",
                (status, task_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(task_id)

    def complete_task(self, task_id: str, status: TaskStatus) -> None:
        """更新任务状态并设置 completed_at 为当前时间。"""
        completed_at = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ?",
                (status, completed_at, task_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(task_id)

    def delete_task(self, task_id: str) -> None:
        """从数据库中删除任务记录。不影响输出文件和原始文件。"""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM tasks WHERE task_id = ?",
                (task_id,),
            )
        if cursor.rowcount != 1:
            raise KeyError(task_id)

    def request_task_action(
        self,
        task_id: str,
        action: RequestedTaskAction,
    ) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE tasks SET requested_action = ?
                WHERE task_id = ? AND status = 'running'
                """,
                (action, task_id),
            )
        if cursor.rowcount != 1:
            raise ValueError("task is not running")

    def apply_requested_action(self, task_id: str) -> TaskRecord:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT requested_action FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            action = row["requested_action"]
            if action is not None:
                next_status = "paused" if action == "pause" else "cancelled"
                self._connection.execute(
                    """
                    UPDATE tasks SET status = ?, requested_action = NULL
                    WHERE task_id = ?
                    """,
                    (next_status, task_id),
                )
            updated = self._connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        assert updated is not None
        return self._task_from_row(updated)

    def claim_next_pending_task(self) -> TaskRecord | None:
        with self._lock, self._connection:
            running = self._connection.execute(
                "SELECT 1 FROM tasks WHERE status = 'running' LIMIT 1"
            ).fetchone()
            if running is not None:
                return None
            row = self._connection.execute(
                "SELECT task_id FROM tasks WHERE status = 'pending' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            self._connection.execute(
                "UPDATE tasks SET status = 'running' WHERE task_id = ?",
                (row["task_id"],),
            )
            claimed = self._connection.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (row["task_id"],),
            ).fetchone()
        assert claimed is not None
        return self._task_from_row(claimed)

    def pause_running_tasks(self) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE tasks SET status = 'paused', requested_action = NULL
                WHERE status = 'running'
                """
            )
        return cursor.rowcount

    def save_provider(self, profile: Mapping[str, Any] | BaseModel) -> None:
        payload = profile.model_dump() if isinstance(profile, BaseModel) else dict(profile)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO provider_profiles (
                    profile_id, display_name, adapter_type, endpoint, model, public,
                    capabilities, approved_fallback_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    adapter_type = excluded.adapter_type,
                    endpoint = excluded.endpoint,
                    model = excluded.model,
                    public = excluded.public,
                    capabilities = excluded.capabilities,
                    approved_fallback_ids = excluded.approved_fallback_ids
                """,
                (
                    payload["profile_id"],
                    payload["display_name"],
                    payload["adapter_type"],
                    payload.get("endpoint"),
                    payload.get("model"),
                    int(bool(payload.get("public", True))),
                    json.dumps(payload.get("capabilities", {}), ensure_ascii=False),
                    json.dumps(payload.get("approved_fallback_ids", [])),
                ),
            )

    def get_provider(self, profile_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM provider_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        return self._provider_from_row(row) if row is not None else None

    def list_providers(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM provider_profiles ORDER BY display_name, profile_id"
            ).fetchall()
        return [self._provider_from_row(row) for row in rows]

    def delete_provider(self, profile_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM provider_profiles WHERE profile_id = ?",
                (profile_id,),
            )

    def provider_in_use(self, profile_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT 1 FROM tasks
                WHERE provider_profile_id = ? AND status = 'running'
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
        return row is not None

    def provider_columns(self) -> list[str]:
        with self._lock:
            rows = self._connection.execute(
                "PRAGMA table_info(provider_profiles)"
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def raw_database_text(self) -> str:
        with self._lock:
            self._connection.commit()
            return self.path.read_bytes().decode("utf-8", errors="ignore")

    def _migrate(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    source_path TEXT,
                    sensitive INTEGER NOT NULL,
                    selected_pages TEXT NOT NULL,
                    provider_profile_id TEXT NOT NULL,
                    approved_fallback_ids TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    quality_rating TEXT,
                    requested_action TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    processing_mode TEXT NOT NULL DEFAULT 'ocr',
                    ocr_provider_profile_id TEXT,
                    translation_provider_profile_id TEXT,
                    target_language TEXT,
                    translation_mode TEXT
                );

                CREATE TABLE IF NOT EXISTS provider_profiles (
                    profile_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    adapter_type TEXT NOT NULL,
                    endpoint TEXT,
                    model TEXT,
                    public INTEGER NOT NULL,
                    capabilities TEXT NOT NULL,
                    approved_fallback_ids TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            row = self._connection.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            elif int(row["version"]) != SCHEMA_VERSION:
                current_version = int(row["version"])
                if current_version == 1 and SCHEMA_VERSION == 2:
                    self._migrate_v1_to_v2()
                elif current_version == 2 and SCHEMA_VERSION == 3:
                    self._migrate_v2_to_v3()
                elif current_version == 3 and SCHEMA_VERSION == 4:
                    self._migrate_v3_to_v4()
                else:
                    raise RuntimeError(
                        f"Unsupported database schema version: {current_version}"
                    )

    def _migrate_v1_to_v2(self) -> None:
        """从 schema v1 升级到 v2：添加 completed_at 列。"""
        with self._lock, self._connection:
            self._connection.execute(
                "ALTER TABLE tasks ADD COLUMN completed_at TEXT"
            )
            self._connection.execute(
                "UPDATE schema_version SET version = ?",
                (SCHEMA_VERSION,),
            )

    def _migrate_v2_to_v3(self) -> None:
        """从 schema v2 升级到 v3：添加 model 列和 preferences 表。"""
        with self._lock, self._connection:
            # 添加 model 列（如果不存在）
            cols = {
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(provider_profiles)"
                ).fetchall()
            }
            if "model" not in cols:
                self._connection.execute(
                    "ALTER TABLE provider_profiles ADD COLUMN model TEXT"
                )
            # 创建 preferences 表
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                "UPDATE schema_version SET version = ?",
                (SCHEMA_VERSION,),
            )

    def _migrate_v3_to_v4(self) -> None:
        """从 schema v3 升级到 v4：tasks 表增加 AI Processing 字段。"""
        with self._lock, self._connection:
            task_cols = {
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(tasks)"
                ).fetchall()
            }
            new_task_columns = {
                "processing_mode": "TEXT NOT NULL DEFAULT 'ocr'",
                "ocr_provider_profile_id": "TEXT",
                "translation_provider_profile_id": "TEXT",
                "target_language": "TEXT",
                "translation_mode": "TEXT",
            }
            for col, definition in new_task_columns.items():
                if col not in task_cols:
                    self._connection.execute(
                        f"ALTER TABLE tasks ADD COLUMN {col} {definition}"
                    )
            # 历史 OCR 任务：ocr_provider_profile_id 回退到 provider_profile_id。
            if "ocr_provider_profile_id" not in task_cols:
                self._connection.execute(
                    """
                    UPDATE tasks
                    SET ocr_provider_profile_id = provider_profile_id
                    WHERE ocr_provider_profile_id IS NULL
                    """
                )
            self._connection.execute(
                "UPDATE schema_version SET version = ?",
                (SCHEMA_VERSION,),
            )

    def get_preferences(self) -> dict[str, str]:
        """返回所有偏好设置。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT key, value FROM preferences"
            ).fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    def set_preference(self, key: str, value: str) -> None:
        """设置单个偏好项（UPSERT）。"""
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO preferences (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def set_preferences(self, prefs: dict[str, str]) -> None:
        """批量设置偏好项。"""
        with self._lock, self._connection:
            for key, value in prefs.items():
                self._connection.execute(
                    """
                    INSERT INTO preferences (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, str(value)),
                )

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            display_name=row["display_name"],
            source_path=row["source_path"],
            sensitive=bool(row["sensitive"]),
            selected_pages=json.loads(row["selected_pages"]),
            provider_profile_id=row["provider_profile_id"],
            approved_fallback_ids=json.loads(row["approved_fallback_ids"]),
            status=row["status"],
            output_dir=row["output_dir"],
            quality_rating=row["quality_rating"],
            requested_action=row["requested_action"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            processing_mode=row["processing_mode"],
            ocr_provider_profile_id=row["ocr_provider_profile_id"],
            translation_provider_profile_id=row["translation_provider_profile_id"],
            target_language=row["target_language"],
            translation_mode=row["translation_mode"],
        )

    @staticmethod
    def _provider_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "profile_id": row["profile_id"],
            "display_name": row["display_name"],
            "adapter_type": row["adapter_type"],
            "endpoint": row["endpoint"],
            "model": row["model"],
            "public": bool(row["public"]),
            "capabilities": json.loads(row["capabilities"]),
            "approved_fallback_ids": json.loads(row["approved_fallback_ids"]),
        }
