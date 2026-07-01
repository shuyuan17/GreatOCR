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


class NewTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: str
    sensitive: bool = False
    pages: list[int] = Field(default_factory=list)
    provider_profile_id: str = "mineru-default"
    output_dir: str | None = None
    approved_fallback_ids: list[str] = Field(default_factory=list)

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
    created_at: str
