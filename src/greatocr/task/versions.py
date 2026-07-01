from __future__ import annotations

import re
import shutil
from pathlib import Path


_VERSION_PATTERN = re.compile(r"^result-v(\d+)\.docx$")


def publish_result_version(task_dir: Path, generated: Path) -> Path:
    if not generated.is_file():
        raise FileNotFoundError(f"generated DOCX does not exist: {generated}")
    task_dir.mkdir(parents=True, exist_ok=True)
    latest = task_dir / "result.docx"
    existing = _existing_versions(task_dir)

    if latest.is_file() and not existing and latest.resolve() != generated.resolve():
        initial = task_dir / "result-v1.docx"
        shutil.copy2(latest, initial)
        existing[1] = initial

    next_version = max(existing, default=0) + 1
    versioned = task_dir / f"result-v{next_version}.docx"
    shutil.copy2(generated, versioned)

    pending_latest = task_dir / ".result.docx.tmp"
    shutil.copy2(versioned, pending_latest)
    pending_latest.replace(latest)
    return versioned


def _existing_versions(task_dir: Path) -> dict[int, Path]:
    versions: dict[int, Path] = {}
    for path in task_dir.glob("result-v*.docx"):
        match = _VERSION_PATTERN.match(path.name)
        if match:
            versions[int(match.group(1))] = path
    return versions
