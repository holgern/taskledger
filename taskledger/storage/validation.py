from __future__ import annotations

from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.models import ProjectPaths
from taskledger.storage.common import load_json_array as _load_json_array
from taskledger.storage.common import write_json as _write_json
from taskledger.timeutils import utc_now_iso

ValidationRecordKind = str


def validation_records_dir(paths: ProjectPaths) -> Path:
    return paths.project_dir / "validation"


def validation_records_index_path(paths: ProjectPaths) -> Path:
    return validation_records_dir(paths) / "index.json"


def load_validation_records(paths: ProjectPaths) -> list[dict[str, object]]:
    index = validation_records_index_path(paths)
    if not index.exists():
        return []
    return [
        _normalize_validation_record(item)
        for item in _load_json_array(index, "project validation record index")
    ]


def save_validation_records(
    paths: ProjectPaths,
    records: list[dict[str, object]],
) -> None:
    _write_json(
        validation_records_index_path(paths),
        [_normalize_validation_record(item) for item in records],
    )


def append_validation_record(
    paths: ProjectPaths,
    *,
    project_item_ref: str,
    memory_ref: str,
    kind: ValidationRecordKind,
    run_id: str | None = None,
    status: str | None = None,
    verdict: str | None = None,
    source: dict[str, object] | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    records = load_validation_records(paths)
    record_id = _next_id(
        "val",
        [str(item.get("id", "")) for item in records],
    )
    record: dict[str, object] = {
        "id": record_id,
        "created_at": utc_now_iso(),
        "project_item_ref": project_item_ref,
        "memory_ref": memory_ref,
        "kind": kind,
    }
    if run_id is not None:
        record["run_id"] = run_id
    if status is not None:
        record["status"] = status
    if verdict is not None:
        record["verdict"] = verdict
    if source is not None:
        record["source"] = dict(source)
    if notes is not None:
        record["notes"] = notes
    records.append(record)
    save_validation_records(paths, records)
    return record


def remove_validation_records(
    paths: ProjectPaths,
    *,
    ids: set[str],
) -> list[dict[str, object]]:
    if not ids:
        return []
    records = load_validation_records(paths)
    removed = [item for item in records if str(item.get("id")) in ids]
    remaining = [item for item in records if str(item.get("id")) not in ids]
    if len(remaining) != len(records):
        save_validation_records(paths, remaining)
    return removed


def _normalize_validation_record(data: dict[str, object]) -> dict[str, object]:
    project_item_ref = _required_string(data, "project_item_ref")
    memory_ref = _required_string(data, "memory_ref")
    record_id = _required_string(data, "id")
    created_at = _required_string(data, "created_at")
    kind = _required_string(data, "kind")
    normalized: dict[str, object] = {
        "id": record_id,
        "created_at": created_at,
        "project_item_ref": project_item_ref,
        "memory_ref": memory_ref,
        "kind": kind,
    }
    for key in ("run_id", "status", "verdict", "notes"):
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise LaunchError(f"Validation record field '{key}' must be a string.")
        normalized[key] = value
    source = data.get("source")
    if source is not None:
        if not isinstance(source, dict):
            raise LaunchError("Validation record field 'source' must be an object.")
        normalized["source"] = source
    return normalized


def _required_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LaunchError(
            f"Validation record field '{key}' must be a non-empty string."
        )
    return value
