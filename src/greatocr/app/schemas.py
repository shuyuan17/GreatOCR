from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TaskStatus = Literal[
    "pending",
    "running",
    "paused",
    "succeeded",
    "partial",
    "failed",
    "cancelled",
]
RequestedTaskAction = Literal["pause", "cancel"]

# 处理模式：仅 OCR，或 OCR + 翻译。
ProcessingMode = Literal["ocr", "translation"]


class NewTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: str
    sensitive: bool = False
    pages: list[int] = Field(default_factory=list)
    provider_profile_id: str = "mineru-default"
    output_dir: str | None = None
    approved_fallback_ids: list[str] = Field(default_factory=list)

    # ----- AI Processing 扩展字段（OCR + 翻译 MVP）-----
    # 处理模式。向后兼容：缺省为 "ocr"（等同于现有 OCR 流程）。
    processing_mode: ProcessingMode = "ocr"
    # OCR Provider（新字段）。缺省时回退到 provider_profile_id，保持兼容。
    ocr_provider_profile_id: str | None = None
    # 翻译 Provider（translation 模式必填）。
    translation_provider_profile_id: str | None = None
    # 翻译目标语言（translation 模式使用）。
    target_language: str | None = None
    # 翻译模式（当前仅 "page" 即逐页翻译）。
    translation_mode: str | None = None

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, pages: list[int]) -> list[int]:
        if any(page < 1 for page in pages):
            raise ValueError("selected pages must be positive")
        return list(dict.fromkeys(pages))


class TaskRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str
    display_name: str
    source_path: str | None
    sensitive: bool
    selected_pages: list[int]
    provider_profile_id: str
    approved_fallback_ids: list[str] = Field(default_factory=list)
    status: TaskStatus
    output_dir: str
    quality_rating: str | None = None
    requested_action: RequestedTaskAction | None = None
    created_at: str
    completed_at: str | None = None

    # ----- AI Processing 扩展字段 -----
    processing_mode: ProcessingMode = "ocr"
    ocr_provider_profile_id: str | None = None
    translation_provider_profile_id: str | None = None
    target_language: str | None = None
    translation_mode: str | None = None


class TaskResultFileEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    filename: str
    exists: bool
    download_path: str | None = None


class TaskResultSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    task: TaskRecord
    files: dict[str, TaskResultFileEntry]


class DefaultOutputDirResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir: str
