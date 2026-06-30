from __future__ import annotations

import time
from dataclasses import dataclass, field


DEFAULT_STAGE_WEIGHTS = {
    "preflight": 0.1,
    "submit": 0.15,
    "parse": 0.35,
    "model": 0.15,
    "docx": 0.15,
    "quality": 0.1,
}


@dataclass(frozen=True)
class ProgressSnapshot:
    stage: str
    percent: int
    elapsed_seconds: float
    estimated_remaining_seconds: float | None


@dataclass
class ProgressTracker:
    stage_weights: dict[str, float] = field(default_factory=lambda: DEFAULT_STAGE_WEIGHTS.copy())
    total_pages: int | None = None
    started_at: float = field(default_factory=time.monotonic)
    elapsed_seconds: float | None = None

    def snapshot(
        self,
        *,
        current_stage: str,
        stage_fraction: float | None = None,
        processed_pages: int | None = None,
    ) -> ProgressSnapshot:
        elapsed = self.elapsed_seconds
        if elapsed is None:
            elapsed = max(0.0, time.monotonic() - self.started_at)

        if stage_fraction is None and self.total_pages and processed_pages is not None:
            stage_fraction = min(1.0, max(0.0, processed_pages / self.total_pages))
        stage_fraction = stage_fraction or 0.0

        percent = self._percent(current_stage, stage_fraction)
        eta = self._eta(elapsed, processed_pages)
        return ProgressSnapshot(
            stage=current_stage,
            percent=percent,
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=eta,
        )

    def _percent(self, current_stage: str, stage_fraction: float) -> int:
        completed = 0.0
        for stage, weight in self.stage_weights.items():
            if stage == current_stage:
                completed += weight * stage_fraction
                break
            completed += weight
        return round(completed * 100)

    def _eta(self, elapsed: float, processed_pages: int | None) -> float | None:
        if not self.total_pages or not processed_pages:
            return None
        rate = elapsed / processed_pages
        return max(0.0, rate * (self.total_pages - processed_pages))


def format_progress_bar(percent: int, *, width: int = 20) -> str:
    clamped = min(100, max(0, percent))
    filled = round(width * clamped / 100)
    return f"[{'#' * filled}{'-' * (width - filled)}] {clamped}%"
