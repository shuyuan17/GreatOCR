from __future__ import annotations

from pathlib import Path


_DEFAULT_OUTPUT_STEM = "GreatOCR_Result"


def output_stem(source_name: str | None) -> str:
    if not source_name:
        return _DEFAULT_OUTPUT_STEM
    stem = Path(source_name).stem.strip()
    return stem or _DEFAULT_OUTPUT_STEM


def result_docx_name(source_name: str | None) -> str:
    return f"{output_stem(source_name)}.docx"


def translated_docx_name(source_name: str | None) -> str:
    return f"{output_stem(source_name)}_翻译.docx"


def internal_versions_dir(task_dir: Path) -> Path:
    return task_dir / "intermediates" / "versions"
