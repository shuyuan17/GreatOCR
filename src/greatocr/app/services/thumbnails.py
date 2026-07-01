from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class Thumbnail:
    page_number: int
    path: Path


class ThumbnailService:
    def __init__(self, cache_dir: Path, *, max_cached_pages: int = 20) -> None:
        if max_cached_pages < 1:
            raise ValueError("thumbnail cache size must be positive")
        self.cache_dir = cache_dir
        self.max_cached_pages = max_cached_pages

    def render(self, pdf_path: Path, *, pages) -> list[Thumbnail]:
        requested = list(dict.fromkeys(int(page) for page in pages))
        if len(requested) > self.max_cached_pages:
            raise ValueError("requested thumbnail window exceeds cache limit")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        prefix = hashlib.sha256(str(pdf_path.resolve()).encode("utf-8")).hexdigest()[:12]
        rendered: list[Thumbnail] = []

        with fitz.open(pdf_path) as document:
            for page_number in requested:
                if page_number < 1 or page_number > document.page_count:
                    raise ValueError(f"page {page_number} is outside PDF range")
                target = self.cache_dir / f"{prefix}-page-{page_number:06d}.png"
                if not target.exists():
                    page = document.load_page(page_number - 1)
                    page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False).save(
                        target
                    )
                target.touch()
                rendered.append(Thumbnail(page_number=page_number, path=target))

        self._evict_oldest()
        return rendered

    def _evict_oldest(self) -> None:
        cached = sorted(
            self.cache_dir.glob("*.png"),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        for path in cached[self.max_cached_pages :]:
            path.unlink()
