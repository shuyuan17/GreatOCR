from __future__ import annotations

import re
from datetime import datetime
from hashlib import sha256
from pathlib import Path


_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_UNDERSCORES = re.compile(r"_+")


def safe_stem(name: str) -> str:
    stem = Path(name).stem
    safe = _UNSAFE_CHARS.sub("_", stem).strip("._-")
    safe = _UNDERSCORES.sub("_", safe)
    return safe or "document"


def make_task_dir(base_dir: Path, source_pdf: Path, created_at: datetime) -> Path:
    fingerprint = sha256(source_pdf.read_bytes()).hexdigest()[:8]
    timestamp = created_at.strftime("%Y%m%d-%H%M%S")
    task_dir = base_dir / f"{safe_stem(source_pdf.name)}_{timestamp}_{fingerprint}"
    task_dir.mkdir(parents=True, exist_ok=False)
    return task_dir
