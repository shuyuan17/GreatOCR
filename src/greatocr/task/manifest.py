from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StageStatus = Literal["pending", "running", "succeeded", "failed", "skipped"]


class StageRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: StageStatus
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str | None = None


class TaskManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_fingerprint: str
    config: dict = Field(default_factory=dict)
    stages: dict[str, StageRecord] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)


def save_manifest(manifest: TaskManifest, path: Path) -> Path:
    payload = manifest.model_dump(mode="json")
    payload["config"] = _redact(payload.get("config", {}))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_manifest(path: Path) -> TaskManifest:
    return TaskManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _redact(value):
    if isinstance(value, dict):
        return {
            key: "***" if "key" in key.lower() or "secret" in key.lower() else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
