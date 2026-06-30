from __future__ import annotations

from pathlib import Path

from greatocr.task.manifest import StageRecord, TaskManifest, load_manifest, save_manifest


def manifest_path(task_dir: Path) -> Path:
    return task_dir / "intermediates" / "task-manifest.json"


def load_or_create_manifest(task_dir: Path, source_fingerprint: str, config: dict) -> TaskManifest:
    path = manifest_path(task_dir)
    if path.exists():
        return load_manifest(path)
    return TaskManifest(source_fingerprint=source_fingerprint, config=config)


def mark_stage(
    task_dir: Path,
    manifest: TaskManifest,
    stage: str,
    status: str,
    *,
    message: str | None = None,
    outputs: dict[str, str] | None = None,
) -> TaskManifest:
    stages = dict(manifest.stages)
    stages[stage] = StageRecord(status=status, message=message)
    merged_outputs = dict(manifest.outputs)
    if outputs:
        merged_outputs.update(outputs)
    updated = manifest.model_copy(update={"stages": stages, "outputs": merged_outputs})
    save_manifest(updated, manifest_path(task_dir))
    return updated
