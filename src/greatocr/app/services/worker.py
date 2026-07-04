from __future__ import annotations

from collections.abc import Callable, Sequence

from greatocr.app.db import TaskDatabase
from greatocr.app.schemas import TaskRecord, TaskStatus


class SerialWorker:
    def __init__(self, database: TaskDatabase) -> None:
        self.database = database
        self._active_task_id: str | None = None

    def recover_interrupted(self) -> int:
        self._active_task_id = None
        return self.database.pause_running_tasks()

    def tick(self) -> TaskRecord | None:
        if self._active_task_id is not None:
            active = self.database.get_task(self._active_task_id)
            if active is not None and active.status == "running":
                return None
            self._active_task_id = None

        claimed = self.database.claim_next_pending_task()
        if claimed is not None:
            self._active_task_id = claimed.task_id
        return claimed

    def finish(self, task_id: str, status: TaskStatus) -> None:
        if status == "running" or status == "pending":
            raise ValueError("finished task must leave the active queue state")
        if self._active_task_id != task_id:
            raise ValueError("task is not active in this worker")
        self.database.complete_task(task_id, status)
        self._active_task_id = None

    def checkpoint(self, task_id: str) -> TaskRecord:
        task = self.database.apply_requested_action(task_id)
        if task.status != "running" and self._active_task_id == task_id:
            self._active_task_id = None
        return task

    def run_once(
        self,
        stages: Sequence[Callable[[TaskRecord], None]],
    ) -> TaskRecord | None:
        task = self.tick()
        if task is None:
            return None
        for stage in stages:
            stage(task)
            task = self.checkpoint(task.task_id)
            if task.status != "running":
                return task
        self.finish(task.task_id, "succeeded")
        return self.database.get_task(task.task_id)
