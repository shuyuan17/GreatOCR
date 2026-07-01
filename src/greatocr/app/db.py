from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path, PurePath
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4

from pydantic import BaseModel

from greatocr.app.schemas import NewTask, TaskRecord


SCHEMA_VERSION = 1


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
        )
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO tasks (
                    task_id, display_name, source_path, sensitive, selected_pages,
                    provider_profile_id, approved_fallback_ids, status, output_dir,
                    quality_rating, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    record.created_at,
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

    def save_provider(self, profile: Mapping[str, Any] | BaseModel) -> None:
        payload = profile.model_dump() if isinstance(profile, BaseModel) else dict(profile)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO provider_profiles (
                    profile_id, display_name, adapter_type, endpoint, public,
                    capabilities, approved_fallback_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    adapter_type = excluded.adapter_type,
                    endpoint = excluded.endpoint,
                    public = excluded.public,
                    capabilities = excluded.capabilities,
                    approved_fallback_ids = excluded.approved_fallback_ids
                """,
                (
                    payload["profile_id"],
                    payload["display_name"],
                    payload["adapter_type"],
                    payload.get("endpoint"),
                    int(bool(payload.get("public", True))),
                    json.dumps(payload.get("capabilities", {}), ensure_ascii=False),
                    json.dumps(payload.get("approved_fallback_ids", [])),
                ),
            )

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
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS provider_profiles (
                    profile_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    adapter_type TEXT NOT NULL,
                    endpoint TEXT,
                    public INTEGER NOT NULL,
                    capabilities TEXT NOT NULL,
                    approved_fallback_ids TEXT NOT NULL
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
                raise RuntimeError(
                    f"Unsupported database schema version: {row['version']}"
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
            created_at=row["created_at"],
        )
