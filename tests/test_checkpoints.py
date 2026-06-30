from pathlib import Path

import pytest
from pydantic import ValidationError

from greatocr.task.manifest import StageRecord, TaskManifest, load_manifest, save_manifest


def test_manifest_records_fingerprint_config_stages_and_outputs(tmp_path: Path) -> None:
    manifest = TaskManifest(
        source_fingerprint="a" * 64,
        config={"provider": "fake"},
        stages={"parse": StageRecord(status="succeeded")},
        outputs={"result": "result.docx"},
    )

    save_manifest(manifest, tmp_path / "task-manifest.json")
    loaded = load_manifest(tmp_path / "task-manifest.json")

    assert loaded.source_fingerprint == "a" * 64
    assert loaded.config["provider"] == "fake"
    assert loaded.stages["parse"].status == "succeeded"
    assert loaded.outputs["result"] == "result.docx"


def test_stage_status_is_restricted() -> None:
    with pytest.raises(ValidationError):
        StageRecord(status="done")


def test_manifest_does_not_save_api_key(tmp_path: Path) -> None:
    manifest = TaskManifest(
        source_fingerprint="a" * 64,
        config={"provider": {"api_key": "secret", "name": "mineru"}},
    )

    save_manifest(manifest, tmp_path / "task-manifest.json")
    text = (tmp_path / "task-manifest.json").read_text(encoding="utf-8")

    assert "secret" not in text
    assert "***" in text
