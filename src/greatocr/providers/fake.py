from __future__ import annotations

import shutil
from pathlib import Path

from greatocr.providers.base import DocumentParser, ParserJobResult, ProviderCapabilities


class FakeDocumentParser(DocumentParser):
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=True,
            tables=True,
            formulas=False,
            languages=["auto", "en", "zh"],
            data_residency="local-fixture",
        )

    def parse_document(self, source_pdf: Path, raw_result_dir: Path) -> ParserJobResult:
        if not source_pdf.exists():
            raise FileNotFoundError(f"input file does not exist: {source_pdf}")

        raw_result_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.fixture_path, raw_result_dir / "result.json")
        return ParserJobResult(
            provider_name="fake",
            raw_result_dir=raw_result_dir,
            metadata={"fixture": str(self.fixture_path)},
        )
