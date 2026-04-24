from __future__ import annotations

from pathlib import Path

from taskledger.api.types import ValidationRecord
from taskledger.storage import append_validation_record as _append_validation_record
from taskledger.storage import load_project_state
from taskledger.storage import load_validation_records as _load_validation_records
from taskledger.storage import remove_validation_records as _remove_validation_records


def list_validation_records(workspace_root: Path) -> list[ValidationRecord]:
    return _load_validation_records(load_project_state(workspace_root).paths)


def append_validation_record(workspace_root: Path, **kwargs: object) -> ValidationRecord:
    return _append_validation_record(load_project_state(workspace_root).paths, **kwargs)  # type: ignore[arg-type]


def remove_validation_records(
    workspace_root: Path,
    *,
    ids: set[str],
) -> list[ValidationRecord]:
    return _remove_validation_records(load_project_state(workspace_root).paths, ids=ids)


def append_validation_entry(workspace_root: Path, **kwargs: object) -> ValidationRecord:
    return append_validation_record(workspace_root, **kwargs)


def remove_validation_entries(
    workspace_root: Path,
    *,
    ids: set[str],
) -> list[ValidationRecord]:
    return remove_validation_records(workspace_root, ids=ids)


def summarize_validation_records(workspace_root: Path) -> dict[str, object]:
    records = list_validation_records(workspace_root)
    by_kind: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for record in records:
        kind = str(record.get("kind") or "unknown")
        status = str(record.get("status") or "unknown")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
    return {"count": len(records), "by_kind": by_kind, "by_status": by_status}
