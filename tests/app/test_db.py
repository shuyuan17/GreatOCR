from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from greatocr.app.db import TaskDatabase
from greatocr.app.schemas import NewTask


@pytest.fixture
def db(tmp_path: Path) -> TaskDatabase:
    database = TaskDatabase(tmp_path / "greatocr.db")
    yield database
    database.close()


def test_sensitive_task_uses_anonymous_display_name(db: TaskDatabase) -> None:
    task = db.create_task(
        NewTask(source_path="C:/secret/client.pdf", sensitive=True, pages=[2])
    )

    row = db.get_task(task.task_id)

    assert row is not None
    assert row.display_name.startswith("敏感任务 ")
    assert row.source_path is None
    assert "client.pdf" not in db.raw_database_text()


def test_regular_task_round_trips_selected_pages(db: TaskDatabase) -> None:
    task = db.create_task(
        NewTask(
            source_path="C:/documents/contract.pdf",
            sensitive=False,
            pages=[3, 8, 9, 10],
            provider_profile_id="mineru-default",
        )
    )

    row = db.get_task(task.task_id)

    assert row is not None
    assert row.display_name == "contract.pdf"
    assert row.source_path == "C:/documents/contract.pdf"
    assert row.selected_pages == [3, 8, 9, 10]
    assert row.status == "pending"


def test_database_never_stores_api_key(db: TaskDatabase) -> None:
    db.save_provider(
        {
            "profile_id": "mineru-default",
            "display_name": "MinerU",
            "adapter_type": "mineru",
            "endpoint": "https://mineru.net",
            "public": True,
            "api_key": "top-secret",
        }
    )

    assert "top-secret" not in db.raw_database_text()
    assert "api_key" not in db.provider_columns()


def test_database_initializes_explicit_schema_version(db: TaskDatabase) -> None:
    with sqlite3.connect(db.path) as connection:
        version = connection.execute(
            "SELECT version FROM schema_version"
        ).fetchone()

    assert version == (1,)
