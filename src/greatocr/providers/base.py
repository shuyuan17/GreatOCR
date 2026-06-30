from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ProviderCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    native_pdf: bool
    scanned_pdf: bool
    coordinates: bool
    tables: bool
    formulas: bool
    languages: list[str]
    data_residency: str = "provider-defined"


class ParserJobResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_name: str
    raw_result_dir: Path
    metadata: dict[str, str]


class DocumentParser(ABC):
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return parser capabilities without contacting external services."""

    @abstractmethod
    def parse_document(self, source_pdf: Path, raw_result_dir: Path) -> ParserJobResult:
        """Parse a PDF into provider-native raw results."""

