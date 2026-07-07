from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


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
ProcessingMode = Literal["ocr", "translation"]


def normalize_translation_mode(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in {"page", "page by page"}:
        return "page"
    raise ValueError("unsupported translation mode")


class NewTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: str
    sensitive: bool = False
    pages: list[int] = Field(default_factory=list)
    provider_profile_id: str = "mineru-default"
    output_dir: str | None = None
    approved_fallback_ids: list[str] = Field(default_factory=list)
    processing_mode: ProcessingMode = "ocr"
    ocr_provider_profile_id: str | None = None
    translation_provider_profile_id: str | None = None
    target_language: str | None = None
    translation_mode: str | None = None

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, pages: list[int]) -> list[int]:
        if any(page < 1 for page in pages):
            raise ValueError("selected pages must be positive")
        return list(dict.fromkeys(pages))

    @field_validator("translation_mode")
    @classmethod
    def validate_translation_mode(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str | None:
        processing_mode = info.data.get("processing_mode")
        normalized = normalize_translation_mode(value)
        if processing_mode == "translation":
            return normalized or "page"
        return normalized


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
