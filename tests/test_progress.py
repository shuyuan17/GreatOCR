from greatocr.task.progress import ProgressTracker, format_progress_bar


def test_stage_weights_compute_overall_percent() -> None:
    tracker = ProgressTracker(stage_weights={"preflight": 0.2, "parse": 0.6, "docx": 0.2})

    snapshot = tracker.snapshot(current_stage="parse", stage_fraction=0.5)

    assert snapshot.percent == 50


def test_eta_decreases_as_processed_pages_increase() -> None:
    tracker = ProgressTracker(total_pages=10, elapsed_seconds=100)

    early = tracker.snapshot(current_stage="parse", processed_pages=2)
    later = tracker.snapshot(current_stage="parse", processed_pages=5)

    assert later.estimated_remaining_seconds < early.estimated_remaining_seconds


def test_provider_without_page_progress_uses_stage_weight() -> None:
    tracker = ProgressTracker(stage_weights={"parse": 0.5, "docx": 0.5})

    snapshot = tracker.snapshot(current_stage="parse")

    assert snapshot.percent == 0
    assert "parse" in snapshot.stage


def test_format_progress_bar() -> None:
    assert format_progress_bar(50, width=10) == "[#####-----] 50%"
