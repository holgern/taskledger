from __future__ import annotations

from pathlib import Path

from taskledger.storage import (
    append_validation_record as _append_validation_record,
)
from taskledger.storage import (
    load_project_state,
)
from taskledger.storage import (
    load_validation_records as _load_validation_records,
)
from taskledger.storage import (
    remove_validation_records as _remove_validation_records,
)
from taskledger.storage import (
    save_validation_records as _save_validation_records,
)
from taskledger.storage import (
    validation_records_dir as _validation_records_dir,
)
from taskledger.storage import (
    validation_records_index_path as _validation_records_index_path,
)


def append_validation_record(paths, **kwargs):
    return _append_validation_record(paths, **kwargs)


def load_validation_records(paths):
    return _load_validation_records(paths)


def remove_validation_records(paths, *, ids: set[str]):
    return _remove_validation_records(paths, ids=ids)


def save_validation_records(paths, records) -> None:
    _save_validation_records(paths, records)


def validation_records_dir(paths):
    return _validation_records_dir(paths)


def validation_records_index_path(paths):
    return _validation_records_index_path(paths)


def list_validation_records(workspace_root: Path):
    return load_validation_records(load_project_state(workspace_root).paths)


def append_validation_entry(workspace_root: Path, **kwargs):
    return append_validation_record(load_project_state(workspace_root).paths, **kwargs)


def remove_validation_entries(workspace_root: Path, *, ids: set[str]):
    return remove_validation_records(load_project_state(workspace_root).paths, ids=ids)


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
