from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


BlockType = Literal[
    "title",
    "paragraph",
    "list",
    "table",
    "image",
    "header",
    "footer",
    "page_number",
]
PageType = Literal["native_text", "scanned", "mixed"]
PageStatus = Literal["pending", "succeeded", "partial", "failed"]
Severity = Literal["low", "medium", "high"]


class TextSpan(BaseModel):
    model_config = ConfigDict(frozen=False)

    span_id: str
    original_text: str
    current_text: str
    confidence: float = 1.0
    language: str | None = None
    bbox: list[float] | None = None
    source_bbox: list[float] | None = None
    is_critical: bool = False
    critical_type: str | None = None
    modifications: list[dict[str, str]] = Field(default_factory=list)


class TableCell(BaseModel):
    text: str
    row_span: int = 1
    col_span: int = 1
    confidence: float = 1.0


class Table(BaseModel):
    table_id: str
    rows: list[list[TableCell]]
    confidence: float = 1.0
    degraded_to_image: bool = False
    asset_id: str | None = None


class Asset(BaseModel):
    asset_id: str
    asset_type: str
    path: str | None = None
    page_number: int
    bbox: list[float] | None = None
    source_bbox: list[float] | None = None
    content_fingerprint: str | None = None


class Issue(BaseModel):
    issue_id: str
    page_number: int
    issue_type: str
    severity: Severity
    message: str
    related_id: str | None = None
    snippet: str | None = None
    suggestion: str | None = None


class Block(BaseModel):
    block_id: str
    block_type: BlockType
    reading_order: int
    spans: list[TextSpan] = Field(default_factory=list)
    table: Table | None = None
    asset: Asset | None = None
    bbox: list[float] | None = None
    source_bbox: list[float] | None = None
    confidence: float = 1.0
    source: str | None = None


class ProviderTrace(BaseModel):
    provider_name: str
    model_name: str | None = None
    attempt: int = 1
    elapsed_ms: int | None = None


class Page(BaseModel):
    page_id: str
    page_number: int
    original_page_number: int | None = None
    task_page_number: int | None = None
    width: float
    height: float
    effective_width: float | None = None
    effective_height: float | None = None
    rotation: int
    page_type: PageType
    status: PageStatus = "succeeded"
    provider_traces: list[ProviderTrace] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_v2_defaults(self) -> "Page":
        if self.original_page_number is None:
            self.original_page_number = self.page_number
        if self.task_page_number is None:
            self.task_page_number = self.page_number
        rotated = self.rotation % 180 != 0
        if self.effective_width is None:
            self.effective_width = self.height if rotated else self.width
        if self.effective_height is None:
            self.effective_height = self.width if rotated else self.height
        return self


class Document(BaseModel):
    document_id: str
    source_file_name: str
    file_sha256: str
    page_count: int
    provider_name: str
    pages: list[Page]
    assets: list[Asset] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
