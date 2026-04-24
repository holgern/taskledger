from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.api.items import item_summary
from taskledger.api.types import Memory, RunRecord
from taskledger.api.workflows import mark_stage_succeeded as _mark_stage_succeeded
from taskledger.errors import LaunchError
from taskledger.storage import cleanup_runs as _cleanup_runs
from taskledger.storage import delete_run as _delete_run
from taskledger.storage import (
    load_memories,
    load_project_state,
    resolve_work_item,
    update_work_item,
)
from taskledger.storage import load_run_records as _load_run_records
from taskledger.storage import (
    promote_run_report_to_memory as _promote_run_report_to_memory,
)
from taskledger.storage import promote_run_to_memory as _promote_run_to_memory
from taskledger.storage import resolve_run_record as _resolve_run_record


def list_runs(workspace_root: Path, *, limit: int | None = None) -> list[RunRecord]:
    return _load_run_records(load_project_state(workspace_root).paths, limit=limit)


def show_run(workspace_root: Path, run_id: str) -> RunRecord:
    return _resolve_run_record(load_project_state(workspace_root).paths, run_id)


def delete_run(workspace_root: Path, run_id: str) -> RunRecord:
    return _delete_run(load_project_state(workspace_root).paths, run_id)


def cleanup_runs(workspace_root: Path, *, keep: int) -> list[RunRecord]:
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


def cleanup_run_records(workspace_root: Path, *, keep: int) -> list[RunRecord]:
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


def apply_run_result(
    workspace_root: Path,
    run_ref: str,
    *,
    mode: str = "output",
    mark_stage_succeeded: bool = False,
    summary: str | None = None,
) -> dict[str, object]:
    if mode not in {"output", "report"}:
        raise LaunchError("Run apply mode must be 'output' or 'report'.")
    state = load_project_state(workspace_root, recent_runs_limit=0)
    record = _resolve_run_record(state.paths, run_ref)
    related_item = _resolve_related_item(state, record)
    memory = _existing_promoted_memory(state.paths, record, mode=mode)
    if memory is None:
        name = _promoted_memory_name(record, mode=mode, item=related_item)
        if mode == "output":
            _, memory = _promote_run_to_memory(state.paths, record.run_id, name=name)
        else:
            _, memory = _promote_run_report_to_memory(
                state.paths,
                record.run_id,
                name=name,
            )

    attached_to_role = None
    updated_item = related_item
    stage_id = _workflow_stage_id_for_run(state.paths, record)
    if related_item is not None:
        updated_item, attached_to_role = _attach_run_memory(
            state.paths,
            related_item,
            record,
            memory,
            stage_id=stage_id,
        )

    marked_succeeded = False
    if mark_stage_succeeded:
        if updated_item is None or stage_id is None:
            raise LaunchError(
                "Run "
                f"{record.run_id} is not linked to a workflow stage that can "
                "be completed."
            )
        _mark_stage_succeeded(
            workspace_root,
            updated_item.id,
            stage_id,
            run_id=record.run_id,
            summary=summary or memory.summary or record.output_summary,
            save_target=_save_target_ref(updated_item, attached_to_role),
        )
        marked_succeeded = True

    item_payload = (
        item_summary(workspace_root, updated_item.id)["item"]
        if updated_item is not None
        else None
    )
    return {
        "run": {
            "id": record.run_id,
            "item_ref": (
                updated_item.slug
                if updated_item is not None
                else record.project_item_ref
            ),
            "stage": stage_id,
            "status": record.status,
        },
        "applied": {
            "mode": mode,
            "promoted_memory_ref": memory.id,
            "attached_to_role": attached_to_role,
            "marked_stage_succeeded": marked_succeeded,
        },
        "item": item_payload,
    }


def _resolve_related_item(state, record: RunRecord):
    if record.project_item_ref:
        return resolve_work_item(state.paths, record.project_item_ref)
    if record.item_inputs:
        return resolve_work_item(state.paths, record.item_inputs[0])
    return None


def _promoted_memory_name(
    record: RunRecord,
    *,
    mode: str,
    item,
) -> str:
    prefix = item.slug if item is not None else record.run_id
    return f"{prefix} {record.run_id} {mode}"


def _existing_promoted_memory(paths, record: RunRecord, *, mode: str) -> Memory | None:
    expected_suffix = f"{record.run_id} {mode}"
    for memory in load_memories(paths):
        if memory.source_run_id != record.run_id:
            continue
        if memory.name.endswith(expected_suffix):
            return memory
    return None


def _workflow_stage_id_for_run(paths, record: RunRecord) -> str | None:
    from taskledger.workflow import item_stage_records_for_paths

    if record.project_item_ref:
        stage_record = next(
            (
                current
                for current in sorted(
                    item_stage_records_for_paths(paths, record.project_item_ref),
                    key=lambda entry: (
                        entry.updated_at or "",
                        entry.created_at or "",
                        entry.record_id,
                    ),
                    reverse=True,
                )
                if current.run_id == record.run_id
            ),
            None,
        )
        if stage_record is not None:
            return stage_record.stage_id
    return {
        "analysis": "analysis",
        "state": "state",
        "plan": "plan",
        "implementation": "implement",
        "validation": "validate",
    }.get(record.stage)


def _attach_run_memory(
    paths,
    item,
    record: RunRecord,
    memory: Memory,
    *,
    stage_id: str | None,
):
    linked_memories = list(item.linked_memories)
    if memory.id not in linked_memories:
        linked_memories.append(memory.id)
    linked_runs = list(item.linked_runs)
    if record.run_id not in linked_runs:
        linked_runs.append(record.run_id)

    attached_to_role = None
    updates: dict[str, object] = {
        "linked_memories": tuple(linked_memories),
        "linked_runs": tuple(linked_runs),
    }
    role = _memory_role_for_stage(stage_id)
    if role is not None:
        field_name = _memory_field_for_role(role)
        if getattr(item, field_name) is None:
            updates[field_name] = memory.id
            attached_to_role = role
        if role == "implementation" and item.save_target_ref is None:
            updates["save_target_ref"] = memory.id

    updated = replace(item, **updates)
    return update_work_item(paths, item.id, updated), attached_to_role


def _memory_role_for_stage(stage_id: str | None) -> str | None:
    return {
        "analysis": "analysis",
        "state": "current",
        "plan": "plan",
        "implement": "implementation",
        "validate": "validation",
        "validate_summary": "validation",
    }.get(stage_id)


def _memory_field_for_role(role: str) -> str:
    return {
        "analysis": "analysis_memory_ref",
        "current": "state_memory_ref",
        "plan": "plan_memory_ref",
        "implementation": "implementation_memory_ref",
        "validation": "validation_memory_ref",
    }[role]


def _save_target_ref(item, attached_to_role: str | None) -> str | None:
    if attached_to_role is not None:
        return getattr(item, _memory_field_for_role(attached_to_role))
    return item.save_target_ref
