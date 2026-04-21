from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectMemory, ProjectRunRecord
from taskledger.storage import (
    cleanup_runs as _cleanup_runs,
)
from taskledger.storage import (
    create_run_dir as _create_run_dir,
)
from taskledger.storage import (
    delete_run as _delete_run,
)
from taskledger.storage import (
    load_project_state,
)
from taskledger.storage import (
    load_run_records as _load_run_records,
)
from taskledger.storage import (
    promote_run_report_to_memory as _promote_run_report_to_memory,
)
from taskledger.storage import (
    promote_run_to_memory as _promote_run_to_memory,
)
from taskledger.storage import (
    resolve_run_record as _resolve_run_record,
)
from taskledger.storage import (
    save_run_record as _save_run_record,
)


def cleanup_runs(paths, *, keep: int) -> list[ProjectRunRecord]:
    return _cleanup_runs(paths, keep=keep)


def create_run_dir(paths):
    return _create_run_dir(paths)


def delete_run(paths, run_id: str) -> ProjectRunRecord:
    return _delete_run(paths, run_id)


def load_run_records(paths, *, limit: int | None = None) -> list[ProjectRunRecord]:
    return _load_run_records(paths, limit=limit)


def promote_run_report_to_memory(
    paths, run_id: str, *, name: str
) -> tuple[ProjectRunRecord, ProjectMemory]:
    return _promote_run_report_to_memory(paths, run_id, name=name)


def promote_run_to_memory(
    paths, run_id: str, *, name: str
) -> tuple[ProjectRunRecord, ProjectMemory]:
    return _promote_run_to_memory(paths, run_id, name=name)


def resolve_run_record(paths, run_id: str) -> ProjectRunRecord:
    return _resolve_run_record(paths, run_id)


def save_run_record(run_dir, record: ProjectRunRecord) -> None:
    _save_run_record(run_dir, record)


def list_runs(
    workspace_root: Path, *, limit: int | None = None
) -> list[ProjectRunRecord]:
    return load_run_records(load_project_state(workspace_root).paths, limit=limit)


def show_run(workspace_root: Path, run_id: str) -> ProjectRunRecord:
    return resolve_run_record(load_project_state(workspace_root).paths, run_id)


def delete_run_entry(workspace_root: Path, run_id: str) -> ProjectRunRecord:
    return delete_run(load_project_state(workspace_root).paths, run_id)


def cleanup_run_records(
    workspace_root: Path, *, keep: int
) -> list[ProjectRunRecord]:
    return cleanup_runs(load_project_state(workspace_root).paths, keep=keep)


def promote_run_output(
    workspace_root: Path, run_id: str, *, name: str
) -> tuple[ProjectRunRecord, ProjectMemory]:
    return promote_run_to_memory(
        load_project_state(workspace_root).paths,
        run_id,
        name=name,
    )


def promote_run_report(
    workspace_root: Path, run_id: str, *, name: str
) -> tuple[ProjectRunRecord, ProjectMemory]:
    return promote_run_report_to_memory(
        load_project_state(workspace_root).paths,
        run_id,
        name=name,
    )


def summarize_run_inventory(workspace_root: Path) -> dict[str, object]:
    records = list_runs(workspace_root, limit=None)
    by_status: dict[str, int] = {}
    by_origin: dict[str, int] = {}
    for record in records:
        by_status[record.status] = by_status.get(record.status, 0) + 1
        origin = record.origin or "unknown"
        by_origin[origin] = by_origin.get(origin, 0) + 1
    return {
        "count": len(records),
        "by_status": by_status,
        "by_origin": by_origin,
    }
