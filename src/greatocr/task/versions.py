from __future__ import annotations

import re
import shutil
from pathlib import Path

from greatocr.task.output_files import internal_versions_dir

_VERSION_PATTERN = re.compile(r"^result-v(\d+)\.docx$")


def publish_result_version(
    task_dir: Path,
    generated: Path,
    *,
    latest_name: str = "result.docx",
) -> Path:
    if not generated.is_file():
        raise FileNotFoundError(f"generated DOCX does not exist: {generated}")
    task_dir.mkdir(parents=True, exist_ok=True)
    versions_dir = internal_versions_dir(task_dir)
    versions_dir.mkdir(parents=True, exist_ok=True)
    latest = task_dir / latest_name
    existing = _existing_versions(versions_dir)

    if latest.is_file() and not existing and latest.resolve() != generated.resolve():
        initial = versions_dir / "result-v1.docx"
        shutil.copy2(latest, initial)
        existing[1] = initial

    next_version = max(existing, default=0) + 1
    versioned = versions_dir / f"result-v{next_version}.docx"
    shutil.copy2(generated, versioned)

    pending_latest = task_dir / f".{latest_name}.tmp"
    shutil.copy2(versioned, pending_latest)
    pending_latest.replace(latest)
    return versioned


def _existing_versions(versions_dir: Path) -> dict[int, Path]:
    versions: dict[int, Path] = {}
    for path in versions_dir.glob("result-v*.docx"):
        match = _VERSION_PATTERN.match(path.name)
        if match:
            versions[int(match.group(1))] = path
    return versions
