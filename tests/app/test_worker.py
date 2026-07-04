from __future__ import annotations

from pathlib import Path

from greatocr.app.db import TaskDatabase
from greatocr.app.schemas import NewTask
from greatocr.app.services.worker import SerialWorker


def make_task(database: TaskDatabase, name: str):
    return database.create_task(
        NewTask(source_path=f"C:/documents/{name}.pdf", pages=[1])
    )


def test_worker_runs_one_task_and_leaves_second_pending(tmp_path: Path) -> None:
    database = TaskDatabase(tmp_path / "greatocr.db")
    try:
        first = make_task(database, "first")
        second = make_task(database, "second")
        worker = SerialWorker(database)

        claimed = worker.tick()

        assert claimed is not None
        assert claimed.task_id == first.task_id
        assert [database.get_task(task.task_id).status for task in (first, second)] == [
            "running",
            "pending",
        ]
        assert worker.tick() is None
    finally:
        database.close()


def test_worker_claims_next_task_after_current_finishes(tmp_path: Path) -> None:
    database = TaskDatabase(tmp_path / "greatocr.db")
    try:
        first = make_task(database, "first")
        second = make_task(database, "second")
        worker = SerialWorker(database)

        worker.tick()
        worker.finish(first.task_id, "succeeded")
        claimed = worker.tick()

        assert claimed is not None
        assert claimed.task_id == second.task_id
    finally:
        database.close()


def test_worker_recovers_interrupted_running_task_as_paused(tmp_path: Path) -> None:
    database = TaskDatabase(tmp_path / "greatocr.db")
    try:
        task = make_task(database, "interrupted")
        database.update_task_status(task.task_id, "running")

        worker = SerialWorker(database)
        recovered = worker.recover_interrupted()

        assert recovered == 1
        assert database.get_task(task.task_id).status == "paused"
    finally:
        database.close()


def test_worker_honors_pause_request_at_stage_boundary(tmp_path: Path) -> None:
    database = TaskDatabase(tmp_path / "greatocr.db")
    try:
        task = make_task(database, "staged")
        stages_run: list[str] = []

        def first_stage(claimed) -> None:
            stages_run.append("first")
            database.request_task_action(claimed.task_id, "pause")

        def second_stage(claimed) -> None:
            stages_run.append("second")

        worker = SerialWorker(database)
        result = worker.run_once([first_stage, second_stage])

        assert result is not None
        assert result.status == "paused"
        assert result.requested_action is None
        assert stages_run == ["first"]
        assert database.get_task(task.task_id).status == "paused"
    finally:
        database.close()
