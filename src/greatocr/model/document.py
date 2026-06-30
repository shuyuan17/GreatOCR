from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
Severity = Literal["low", "medium", "high"]


class TextSpan(BaseModel):
    model_config = ConfigDict(frozen=False)

    span_id: str
    original_text: str
    current_text: str
    confidence: float = 1.0
    language: str | None = None
    bbox: list[float] | None = None
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
    confidence: float = 1.0
    source: str | None = None


class Page(BaseModel):
    page_id: str
    page_number: int
    width: float
    height: float
    rotation: int
    page_type: PageType
    blocks: list[Block] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)


class Document(BaseModel):
    document_id: str
    source_file_name: str
    file_sha256: str
    page_count: int
    provider_name: str
    pages: list[Page]
    assets: list[Asset] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
