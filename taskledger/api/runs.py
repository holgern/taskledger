from __future__ import annotations

from pathlib import Path

from taskledger.api.types import Memory, RunRecord
from taskledger.storage import cleanup_runs as _cleanup_runs
from taskledger.storage import delete_run as _delete_run
from taskledger.storage import load_project_state
from taskledger.storage import load_run_records as _load_run_records
from taskledger.storage import (
    promote_run_report_to_memory as _promote_run_report_to_memory,
)
from taskledger.storage import promote_run_to_memory as _promote_run_to_memory
from taskledger.storage import resolve_run_record as _resolve_run_record


def list_runs(
    workspace_root: Path, *, limit: int | None = None
) -> list[RunRecord]:
    return _load_run_records(load_project_state(workspace_root).paths, limit=limit)


def show_run(workspace_root: Path, run_id: str) -> RunRecord:
    return _resolve_run_record(load_project_state(workspace_root).paths, run_id)


def delete_run(workspace_root: Path, run_id: str) -> RunRecord:
    return _delete_run(load_project_state(workspace_root).paths, run_id)


def cleanup_runs(
    workspace_root: Path, *, keep: int
) -> list[RunRecord]:
    return _cleanup_runs(load_project_state(workspace_root).paths, keep=keep)


def promote_run_output(
    workspace_root: Path, run_id: str, *, name: str
) -> tuple[RunRecord, Memory]:
    return _promote_run_to_memory(
        load_project_state(workspace_root).paths,
        run_id,
        name=name,
    )


def promote_run_report(
    workspace_root: Path, run_id: str, *, name: str
) -> tuple[RunRecord, Memory]:
    return _promote_run_report_to_memory(
        load_project_state(workspace_root).paths,
        run_id,
        name=name,
    )


def delete_run_entry(workspace_root: Path, run_id: str) -> RunRecord:
    return delete_run(workspace_root, run_id)


def cleanup_run_records(
    workspace_root: Path, *, keep: int
) -> list[RunRecord]:
    return cleanup_runs(workspace_root, keep=keep)


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
