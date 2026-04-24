from __future__ import annotations

import re
import shutil
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.models import ProjectPaths, ProjectRunRecord
from taskledger.storage.common import load_json_object as _load_json_object
from taskledger.storage.common import write_json as _write_json

_RUN_ID_PATTERN = re.compile(r"^run-(\d+)$")


def create_run_dir(paths: ProjectPaths) -> tuple[str, Path]:
    existing_ids = [record.run_id for record in load_run_records(paths, limit=None)]
    if paths.runs_dir.exists():
        existing_ids.extend(
            entry.name for entry in paths.runs_dir.iterdir() if entry.is_dir()
        )
    run_id = _next_id("run", existing_ids)
    run_dir = paths.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


def save_run_record(run_dir: Path, record: ProjectRunRecord) -> None:
    _write_json(run_dir / "record.json", record.to_dict())


def load_run_records(
    paths: ProjectPaths, *, limit: int | None = None
) -> list[ProjectRunRecord]:
    if not paths.runs_dir.exists():
        return []
    records: list[ProjectRunRecord] = []
    run_dirs = sorted(
        [entry for entry in paths.runs_dir.iterdir() if entry.is_dir()],
        key=lambda entry: _run_sort_key(entry.name),
        reverse=True,
    )
    if limit is not None:
        run_dirs = run_dirs[:limit]
    for run_dir in run_dirs:
        record_path = run_dir / "record.json"
        if not record_path.exists():
            continue
        data = _load_json_object(record_path, "project run record")
        records.append(ProjectRunRecord.from_dict(data))
    return records


def resolve_run_record(paths: ProjectPaths, run_id: str) -> ProjectRunRecord:
    for record in load_run_records(paths, limit=None):
        if record.run_id == run_id:
            return record
    raise LaunchError(f"Unknown project run: {run_id}")


def delete_run(paths: ProjectPaths, run_id: str) -> ProjectRunRecord:
    record = resolve_run_record(paths, run_id)
    run_dir = paths.runs_dir / run_id
    if not run_dir.exists():
        raise LaunchError(f"Project run directory does not exist: {run_id}")
    shutil.rmtree(run_dir)
    return record


def cleanup_runs(paths: ProjectPaths, *, keep: int) -> list[ProjectRunRecord]:
    if keep < 0:
        raise LaunchError("Project runs cleanup keep count must be non-negative.")
    deleted: list[ProjectRunRecord] = []
    for record in load_run_records(paths, limit=None)[keep:]:
        deleted.append(delete_run(paths, record.run_id))
    return deleted


def _run_sort_key(name: str) -> tuple[int, str]:
    match = _RUN_ID_PATTERN.match(name)
    if match is None:
        return (-1, name)
    return (int(match.group(1)), name)
