from __future__ import annotations

from taskledger.errors import LaunchError
from taskledger.models import ItemStageRecord, ProjectPaths
from taskledger.storage.common import load_json_array as _load_json_array
from taskledger.storage.common import write_json as _write_json


def load_stage_records(paths: ProjectPaths) -> list[ItemStageRecord]:
    return [
        ItemStageRecord.from_dict(item)
        for item in _load_json_array(paths.stage_index_path, "workflow stage index")
    ]


def save_stage_records(paths: ProjectPaths, records: list[ItemStageRecord]) -> None:
    _write_json(paths.stage_index_path, [record.to_dict() for record in records])


def append_stage_record(
    paths: ProjectPaths, record: ItemStageRecord
) -> ItemStageRecord:
    records = load_stage_records(paths)
    records.append(record)
    save_stage_records(paths, records)
    return record


def item_stage_records(paths: ProjectPaths, item_ref: str) -> list[ItemStageRecord]:
    return [
        record for record in load_stage_records(paths) if record.item_ref == item_ref
    ]


def latest_stage_record(
    paths: ProjectPaths,
    item_ref: str,
    stage_id: str,
) -> ItemStageRecord | None:
    matching = [
        record
        for record in load_stage_records(paths)
        if record.item_ref == item_ref and record.stage_id == stage_id
    ]
    if not matching:
        return None
    return sorted(
        matching,
        key=lambda record: (
            record.updated_at or "",
            record.created_at or "",
            record.record_id,
        ),
    )[-1]


def replace_stage_record(
    paths: ProjectPaths, record: ItemStageRecord
) -> ItemStageRecord:
    records = load_stage_records(paths)
    for index, current in enumerate(records):
        if current.record_id == record.record_id:
            records[index] = record
            save_stage_records(paths, records)
            return record
    raise LaunchError(f"Unknown stage record: {record.record_id}")
