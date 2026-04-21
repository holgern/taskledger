from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.api.types import (
    ItemStageRecord,
    ItemWorkflowState,
    WorkflowDefinition,
    WorkItem,
)
from taskledger.models import utc_now_iso
from taskledger.storage import load_project_state, resolve_work_item, update_work_item
from taskledger.workflow import (
    can_enter_stage_for_item,
    default_workflow_id_for_paths,
    delete_custom_workflow_definition,
    item_stage_records_for_paths,
    item_workflow_state_for_item,
    item_workflow_state_payload,
    latest_stage_record_for_paths,
    list_available_workflows,
    record_stage_transition,
    resolve_available_workflow,
    save_custom_workflow_definition,
    set_default_workflow_for_paths,
    sync_item_workflow_fields,
)


def list_workflows(workspace_root: Path) -> list[WorkflowDefinition]:
    return list(list_available_workflows(load_project_state(workspace_root).paths))


def resolve_workflow(workspace_root: Path, workflow_id: str) -> WorkflowDefinition:
    return resolve_available_workflow(
        load_project_state(workspace_root).paths, workflow_id
    )


def save_workflow_definition(
    workspace_root: Path,
    workflow: WorkflowDefinition,
) -> WorkflowDefinition:
    return save_custom_workflow_definition(
        load_project_state(workspace_root).paths, workflow
    )


def delete_workflow_definition(workspace_root: Path, workflow_id: str) -> None:
    delete_custom_workflow_definition(
        load_project_state(workspace_root).paths, workflow_id
    )


def default_workflow_id(workspace_root: Path) -> str | None:
    return default_workflow_id_for_paths(load_project_state(workspace_root).paths)


def set_default_workflow(workspace_root: Path, workflow_id: str) -> WorkflowDefinition:
    return set_default_workflow_for_paths(
        load_project_state(workspace_root).paths, workflow_id
    )


def assign_item_workflow(
    workspace_root: Path,
    item_ref: str,
    workflow_id: str,
) -> WorkItem:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    workflow = resolve_available_workflow(state.paths, workflow_id)
    updated = update_work_item(
        state.paths,
        item.id,
        replace(
            item,
            workflow_id=workflow.workflow_id,
            current_stage_id=None,
            workflow_status="draft",
            stage_status="not_started",
        ),
    )
    return sync_item_workflow_fields(
        load_project_state(workspace_root, recent_runs_limit=0),
        updated,
    )


def item_workflow_state(workspace_root: Path, item_ref: str) -> ItemWorkflowState:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return item_workflow_state_for_item(state, item)


def describe_item_workflow(workspace_root: Path, item_ref: str) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return item_workflow_state_payload(state, item)


def item_stage_records(
    workspace_root: Path,
    item_ref: str,
) -> list[ItemStageRecord]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    workflow_id = item.workflow_id or default_workflow_id_for_paths(state.paths)
    return item_stage_records_for_paths(state.paths, item.id, workflow_id=workflow_id)


def latest_stage_record(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
) -> ItemStageRecord | None:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    workflow_id = item.workflow_id or default_workflow_id_for_paths(state.paths)
    return latest_stage_record_for_paths(
        state.paths,
        item.id,
        stage_id,
        workflow_id=workflow_id,
    )


def allowed_stage_transitions(workspace_root: Path, item_ref: str) -> tuple[str, ...]:
    return item_workflow_state(workspace_root, item_ref).allowed_next_stages


def can_enter_stage(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
) -> tuple[bool, tuple[str, ...]]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return can_enter_stage_for_item(state, item, stage_id)


def enter_stage(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
    *,
    actor: str | None = None,
) -> ItemStageRecord:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return record_stage_transition(
        state,
        item,
        stage_id=stage_id,
        status="ready",
        actor=actor,
        origin="workflow_api",
    )


def mark_stage_running(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
    *,
    request_id: str | None = None,
) -> ItemStageRecord:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    metadata = {"request_id": request_id} if request_id is not None else None
    return record_stage_transition(
        state,
        item,
        stage_id=stage_id,
        status="running",
        origin="workflow_api",
        metadata=metadata,
    )


def mark_stage_succeeded(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
    *,
    run_id: str | None = None,
    summary: str | None = None,
    save_target: str | None = None,
    validation_record_refs: tuple[str, ...] = (),
) -> ItemStageRecord:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return record_stage_transition(
        state,
        item,
        stage_id=stage_id,
        status="succeeded",
        origin="workflow_api",
        run_id=run_id,
        summary=summary,
        save_target=save_target,
        validation_record_refs=validation_record_refs,
    )


def mark_stage_failed(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
    *,
    run_id: str | None = None,
    summary: str | None = None,
) -> ItemStageRecord:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return record_stage_transition(
        state,
        item,
        stage_id=stage_id,
        status="failed",
        origin="workflow_api",
        run_id=run_id,
        summary=summary,
    )


def mark_stage_needs_review(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
    *,
    reason: str | None = None,
) -> ItemStageRecord:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    metadata = {"reason": reason} if reason is not None else None
    return record_stage_transition(
        state,
        item,
        stage_id=stage_id,
        status="needs_review",
        origin="workflow_api",
        summary=reason,
        metadata=metadata,
    )


def approve_stage(
    workspace_root: Path,
    item_ref: str,
    stage_id: str,
    *,
    actor: str | None = None,
) -> ItemStageRecord:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    approved = update_work_item(
        state.paths,
        item.id,
        replace(
            item,
            approved_at=utc_now_iso(),
            status="approved",
            stage="approval",
            workflow_id=item.workflow_id or default_workflow_id_for_paths(state.paths),
            workflow_status="ready",
            stage_status="ready",
        ),
    )
    refreshed = load_project_state(workspace_root, recent_runs_limit=0)
    return record_stage_transition(
        refreshed,
        approved,
        stage_id=stage_id,
        status="approved",
        actor=actor,
        origin="workflow_api",
    )
