from __future__ import annotations

from dataclasses import replace

from taskledger.context import default_item_plan_prompt
from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.models import (
    ExecutionRequest,
    ExpandedExecutionRequest,
    FileRenderMode,
    ItemStageRecord,
    ItemWorkflowState,
    MemoryUpdateMode,
    ProjectArtifactRule,
    ProjectConfig,
    ProjectPaths,
    ProjectState,
    ProjectWorkItem,
    WorkflowDefinition,
    WorkflowStageDefinition,
    WorkflowStageStatus,
    WorkflowStatus,
    WorkflowTransition,
    utc_now_iso,
)
from taskledger.storage import (
    append_stage_record,
    load_project_config_overrides,
    load_stage_records,
    load_validation_records,
    load_workflow_definitions,
    merge_project_config,
    save_workflow_definitions,
    update_work_item,
)
from taskledger.storage import (
    item_stage_records as _item_stage_records,
)
from taskledger.storage.common import summarize_text

DEFAULT_WORKFLOW_ID = "default-item-v1"
_DONE_DEPENDENCY_STATUSES = {"validated", "closed"}
_DONE_WORKFLOW_STATUSES = {"completed", "closed"}
_READY_STAGE_STATUSES = {"ready", "running", "failed", "needs_review", "succeeded"}
_ACTIONABLE_STAGE_STATUSES = {"ready", "running", "failed", "needs_review"}


def effective_workflow_config(state: ProjectState) -> ProjectConfig:
    return merge_project_config(ProjectConfig(), state.config_overrides)


def builtin_workflow_definitions() -> tuple[WorkflowDefinition, ...]:
    return (
        WorkflowDefinition(
            workflow_id=DEFAULT_WORKFLOW_ID,
            name="Default item workflow",
            version="1",
            default_for_items=True,
            stages=(
                WorkflowStageDefinition(
                    stage_id="plan",
                    label="Plan",
                    kind="analysis",
                    order=10,
                    requires_approval_before_entry=True,
                    allows_human_completion=False,
                    allows_runtime_execution=True,
                    output_kind="plan_text",
                    save_target_rule="item_plan_memory",
                    validation_rule=None,
                    instruction_template_id="item.plan.v1",
                ),
                WorkflowStageDefinition(
                    stage_id="implement",
                    label="Implement",
                    kind="implementation",
                    order=20,
                    requires_approval_before_entry=False,
                    allows_human_completion=False,
                    allows_runtime_execution=True,
                    output_kind="implementation_result",
                    save_target_rule="item_implementation_memory",
                    validation_rule=None,
                    instruction_template_id="item.implement.v1",
                ),
                WorkflowStageDefinition(
                    stage_id="validate",
                    label="Validate",
                    kind="validation",
                    order=30,
                    requires_approval_before_entry=False,
                    allows_human_completion=True,
                    allows_runtime_execution=True,
                    output_kind="validation_result",
                    save_target_rule="validation_record",
                    validation_rule=None,
                    instruction_template_id="item.validate.v1",
                ),
                WorkflowStageDefinition(
                    stage_id="validate_summary",
                    label="Validation Summary",
                    kind="summary",
                    order=40,
                    requires_approval_before_entry=False,
                    allows_human_completion=False,
                    allows_runtime_execution=True,
                    output_kind="validation_summary",
                    save_target_rule="validation_summary_memory",
                    validation_rule="validation_record_required",
                    instruction_template_id="item.validate-summary.v1",
                ),
            ),
            transitions=(
                WorkflowTransition(from_stage=None, to_stage="plan", rule="create"),
                WorkflowTransition(
                    from_stage="plan",
                    to_stage="implement",
                    rule="stage_succeeded",
                ),
                WorkflowTransition(
                    from_stage="implement",
                    to_stage="validate",
                    rule="stage_succeeded",
                ),
                WorkflowTransition(
                    from_stage="validate",
                    to_stage="validate_summary",
                    rule="stage_succeeded",
                ),
            ),
            next_action_policy="first_ready_stage",
        ),
    )


def validate_workflow_definition(workflow: WorkflowDefinition) -> None:
    if not workflow.workflow_id.strip():
        raise LaunchError("Workflow id must not be empty.")
    stage_ids = [stage.stage_id for stage in workflow.stages]
    if len(stage_ids) != len(set(stage_ids)):
        raise LaunchError(f"Workflow {workflow.workflow_id} has duplicate stage ids.")
    if list(stage_ids) != [stage.stage_id for stage in _ordered_stages(workflow)]:
        raise LaunchError(f"Workflow {workflow.workflow_id} stages must be ordered.")
    known_stage_ids = set(stage_ids)
    for transition in workflow.transitions:
        if (
            transition.from_stage is not None
            and transition.from_stage not in known_stage_ids
        ):
            raise LaunchError(
                f"Workflow {workflow.workflow_id} transition references unknown stage "
                f"{transition.from_stage}."
            )
        if transition.to_stage not in known_stage_ids:
            raise LaunchError(
                f"Workflow {workflow.workflow_id} transition references unknown stage "
                f"{transition.to_stage}."
            )


def list_available_workflows(paths) -> tuple[WorkflowDefinition, ...]:
    builtins = {
        workflow.workflow_id: workflow for workflow in builtin_workflow_definitions()
    }
    saved = {
        workflow.workflow_id: workflow for workflow in load_workflow_definitions(paths)
    }
    merged = {**builtins, **saved}
    for workflow in merged.values():
        validate_workflow_definition(workflow)
    return tuple(sorted(merged.values(), key=lambda workflow: workflow.workflow_id))


def resolve_available_workflow(paths, workflow_id: str) -> WorkflowDefinition:
    for workflow in list_available_workflows(paths):
        if workflow.workflow_id == workflow_id:
            return workflow
    raise LaunchError(f"Unknown workflow definition: {workflow_id}")


def default_workflow_id_for_paths(paths) -> str:
    saved = load_workflow_definitions(paths)
    for workflow in saved:
        if workflow.default_for_items:
            return workflow.workflow_id
    for workflow in builtin_workflow_definitions():
        if workflow.default_for_items:
            return workflow.workflow_id
    return DEFAULT_WORKFLOW_ID


def save_custom_workflow_definition(
    paths, workflow: WorkflowDefinition
) -> WorkflowDefinition:
    validate_workflow_definition(workflow)
    builtins = {item.workflow_id for item in builtin_workflow_definitions()}
    existing = load_workflow_definitions(paths)
    if workflow.workflow_id in builtins and workflow.workflow_id not in {
        item.workflow_id for item in existing
    }:
        raise LaunchError(
            "Workflow "
            f"{workflow.workflow_id} is built in; save a custom workflow id instead."
        )
    updated: list[WorkflowDefinition] = []
    found = False
    for current in existing:
        if current.workflow_id == workflow.workflow_id:
            updated.append(workflow)
            found = True
            continue
        if workflow.default_for_items and current.default_for_items:
            updated.append(replace(current, default_for_items=False))
            continue
        updated.append(current)
    if not found:
        updated.append(workflow)
    save_workflow_definitions(paths, updated)
    return workflow


def delete_custom_workflow_definition(paths, workflow_id: str) -> None:
    builtins = {item.workflow_id for item in builtin_workflow_definitions()}
    if workflow_id in builtins:
        raise LaunchError(f"Workflow {workflow_id} is built in and cannot be deleted.")
    remaining = [
        workflow
        for workflow in load_workflow_definitions(paths)
        if workflow.workflow_id != workflow_id
    ]
    if len(remaining) == len(load_workflow_definitions(paths)):
        raise LaunchError(f"Unknown workflow definition: {workflow_id}")
    save_workflow_definitions(paths, remaining)


def set_default_workflow_for_paths(paths, workflow_id: str) -> WorkflowDefinition:
    workflow = resolve_available_workflow(paths, workflow_id)
    existing = load_workflow_definitions(paths)
    updated: list[WorkflowDefinition] = []
    handled = False
    for current in existing:
        if current.workflow_id == workflow_id:
            updated.append(replace(current, default_for_items=True))
            handled = True
            continue
        if current.default_for_items:
            updated.append(replace(current, default_for_items=False))
            continue
        updated.append(current)
    if workflow.workflow_id == DEFAULT_WORKFLOW_ID:
        save_workflow_definitions(paths, updated)
        return workflow
    if not handled:
        updated.append(replace(workflow, default_for_items=True))
    save_workflow_definitions(paths, updated)
    return replace(workflow, default_for_items=True)


def item_stage_records_for_paths(
    paths,
    item_ref: str,
    *,
    workflow_id: str | None = None,
) -> list[ItemStageRecord]:
    records = _item_stage_records(paths, item_ref)
    if workflow_id is None:
        return records
    return [record for record in records if record.workflow_id == workflow_id]


def latest_stage_record_for_paths(
    paths,
    item_ref: str,
    stage_id: str,
    *,
    workflow_id: str | None = None,
) -> ItemStageRecord | None:
    candidates = [
        record
        for record in item_stage_records_for_paths(
            paths, item_ref, workflow_id=workflow_id
        )
        if record.stage_id == stage_id
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda record: (
            record.updated_at or "",
            record.created_at or "",
            record.record_id,
        ),
    )[-1]


def item_workflow_state_for_item(
    state: ProjectState, item: ProjectWorkItem
) -> ItemWorkflowState:
    workflow = resolve_available_workflow(
        state.paths,
        item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    analysis = _analyze_item_workflow(state, item, workflow)
    return analysis["workflow_state"]


def item_workflow_state_payload(
    state: ProjectState, item: ProjectWorkItem
) -> dict[str, object]:
    workflow = resolve_available_workflow(
        state.paths,
        item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    analysis = _analyze_item_workflow(state, item, workflow)
    return {
        "workflow": workflow.to_dict(),
        "state": analysis["workflow_state"].to_dict(),
        "stages": analysis["stages"],
    }


def allowed_stage_transitions_for_item(
    state: ProjectState,
    item: ProjectWorkItem,
) -> tuple[str, ...]:
    return item_workflow_state_for_item(state, item).allowed_next_stages


def can_enter_stage_for_item(
    state: ProjectState,
    item: ProjectWorkItem,
    stage_id: str,
) -> tuple[bool, tuple[str, ...]]:
    workflow = resolve_available_workflow(
        state.paths,
        item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    analysis = _analyze_item_workflow(state, item, workflow)
    stage_detail = next(
        (detail for detail in analysis["stages"] if detail["stage_id"] == stage_id),
        None,
    )
    if stage_detail is None:
        raise LaunchError(
            f"Workflow {workflow.workflow_id} does not define stage {stage_id}."
        )
    return bool(stage_detail["allowed"]), tuple(stage_detail["blocked_by"])


def append_item_stage_record(
    paths,
    item: ProjectWorkItem,
    *,
    stage_id: str,
    status: str,
    actor: str | None = None,
    origin: str | None = None,
    run_id: str | None = None,
    summary: str | None = None,
    save_target: str | None = None,
    validation_record_refs: tuple[str, ...] = (),
    metadata: dict[str, object] | None = None,
) -> ItemStageRecord:
    records = load_stage_records(paths)
    now = utc_now_iso()
    record = ItemStageRecord(
        record_id=_next_id("stg", [entry.record_id for entry in records]),
        item_ref=item.id,
        workflow_id=item.workflow_id or default_workflow_id_for_paths(paths),
        stage_id=stage_id,
        status=status,
        origin=origin,
        requested_by=actor,
        run_id=run_id,
        validation_record_refs=validation_record_refs,
        output_summary=summary,
        save_target=save_target,
        created_at=now,
        updated_at=now,
        metadata=metadata,
    )
    append_stage_record(paths, record)
    return record


def sync_item_workflow_fields(
    state: ProjectState,
    item: ProjectWorkItem,
) -> ProjectWorkItem:
    workflow = resolve_available_workflow(
        state.paths,
        item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    analysis = _analyze_item_workflow(state, item, workflow)
    workflow_state = analysis["workflow_state"]
    status, stage = _legacy_status_and_stage(item, workflow_state)
    updated = replace(
        item,
        workflow_id=workflow.workflow_id,
        current_stage_id=workflow_state.current_stage_id,
        workflow_status=workflow_state.workflow_status,
        stage_status=workflow_state.stage_status,
        status=status,
        stage=stage,
    )
    return update_work_item(state.paths, item.id, updated)


def build_workflow_summary(state: ProjectState) -> dict[str, object]:
    config = effective_workflow_config(state)
    if config.artifact_rules:
        return _legacy_config_workflow_summary(state, config)
    items = list(state.work_items)
    default_workflow = resolve_available_workflow(
        state.paths,
        default_workflow_id_for_paths(state.paths),
    )
    item_lookup = {item.id: item for item in items}
    item_states = [
        _workflow_item_summary(
            state,
            item,
            workflow=resolve_available_workflow(
                state.paths,
                item.workflow_id or default_workflow.workflow_id,
            ),
            item_lookup=item_lookup,
        )
        for item in items
    ]
    counts = {
        "ready": sum(1 for item in item_states if item["workflow_status"] == "ready"),
        "blocked": sum(
            1
            for item in item_states
            if item["workflow_status"]
            in {"blocked", "waiting_approval", "waiting_validation"}
        ),
        "done": sum(
            1
            for item in item_states
            if item["workflow_status"] in {"completed", "closed"}
        ),
    }
    return {
        "schema": config.workflow_schema or default_workflow.workflow_id,
        "project_context": config.project_context,
        "default_artifact_order": list(config.default_artifact_order)
        or [stage.stage_id for stage in _ordered_stages(default_workflow)],
        "artifact_rules": [
            rule.to_dict()
            for rule in _artifact_rules_for_summary(config, default_workflow)
        ],
        "workflows": [
            workflow.to_dict() for workflow in list_available_workflows(state.paths)
        ],
        "counts": counts,
        "ready_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "ready"
        ],
        "blocked_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"]
            in {"blocked", "waiting_approval", "waiting_validation"}
        ],
        "done_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] in {"completed", "closed"}
        ],
        "items": item_states,
    }


def choose_next_workflow_item(state: ProjectState) -> dict[str, object] | None:
    workflow = build_workflow_summary(state)
    items = workflow["items"]
    assert isinstance(items, list)
    ranked_ready = sorted(
        [
            item
            for item in items
            if isinstance(item, dict) and item.get("workflow_status") == "ready"
        ],
        key=_item_sort_key,
    )
    if ranked_ready:
        return ranked_ready[0]
    ranked_blocked = sorted(
        [
            item
            for item in items
            if isinstance(item, dict)
            and item.get("workflow_status")
            in {"blocked", "waiting_approval", "waiting_validation"}
        ],
        key=_item_sort_key,
    )
    if ranked_blocked:
        return ranked_blocked[0]
    return None


def _legacy_config_workflow_summary(
    state: ProjectState,
    config: ProjectConfig,
) -> dict[str, object]:
    rules = _ordered_artifact_rules(config)
    memory_state = _legacy_memory_completion_state(state)
    item_lookup = {item.id: item for item in state.work_items}
    item_states = [
        _legacy_item_workflow_state(
            item,
            rules=rules,
            item_lookup=item_lookup,
            memory_state=memory_state,
        )
        for item in state.work_items
    ]
    counts = {
        "ready": sum(1 for item in item_states if item["workflow_status"] == "ready"),
        "blocked": sum(
            1 for item in item_states if item["workflow_status"] == "blocked"
        ),
        "done": sum(1 for item in item_states if item["workflow_status"] == "done"),
    }
    return {
        "schema": config.workflow_schema,
        "project_context": config.project_context,
        "default_artifact_order": [rule.name for rule in rules],
        "artifact_rules": [rule.to_dict() for rule in rules],
        "workflows": [
            workflow.to_dict() for workflow in list_available_workflows(state.paths)
        ],
        "counts": counts,
        "ready_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "ready"
        ],
        "blocked_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "blocked"
        ],
        "done_items": [
            item["item_ref"]
            for item in item_states
            if item["workflow_status"] == "done"
        ],
        "items": item_states,
    }


def build_execution_request_for_item(
    state: ProjectState,
    item: ProjectWorkItem,
    *,
    stage_id: str,
    context_inputs: tuple[str, ...] = (),
    memory_inputs: tuple[str, ...] = (),
    file_inputs: tuple[str, ...] = (),
    directory_inputs: tuple[str, ...] = (),
    item_inputs: tuple[str, ...] = (),
    inline_inputs: tuple[str, ...] = (),
    loop_artifact_inputs: tuple[str, ...] = (),
    prompt_seed: str | None = None,
    run_in_repo: str | None = None,
    save_mode: MemoryUpdateMode | None = None,
    file_render_mode: FileRenderMode = "content",
) -> ExecutionRequest:
    workflow = resolve_available_workflow(
        state.paths,
        item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    stage = _resolve_stage(workflow, stage_id)
    can_enter, reasons = can_enter_stage_for_item(state, item, stage_id)
    if not can_enter:
        raise LaunchError(
            f"Stage {stage_id} cannot be entered for {item.id}: {', '.join(reasons)}"
        )
    request_ids = _request_ids_for_paths(state.paths)
    return ExecutionRequest(
        request_id=_next_id("req", request_ids),
        item_ref=item.id,
        workflow_id=workflow.workflow_id,
        stage_id=stage.stage_id,
        context_inputs=context_inputs,
        memory_inputs=memory_inputs,
        file_inputs=file_inputs,
        directory_inputs=directory_inputs,
        item_inputs=item_inputs,
        inline_inputs=inline_inputs,
        loop_artifact_inputs=loop_artifact_inputs,
        instruction_template_id=stage.instruction_template_id,
        prompt_seed=prompt_seed or _prompt_seed_for_stage(item, stage.stage_id),
        run_in_repo=run_in_repo or item.target_repo_ref,
        save_target=_resolve_save_target(item, stage),
        save_mode=save_mode,
        file_render_mode=file_render_mode,
        metadata={"stage_label": stage.label, "workflow_name": workflow.name},
    )


def update_item_for_approval(
    state: ProjectState, item: ProjectWorkItem
) -> ProjectWorkItem:
    return update_work_item(
        state.paths,
        item.id,
        replace(
            item,
            workflow_id=item.workflow_id or default_workflow_id_for_paths(state.paths),
            workflow_status="ready",
            stage_status="ready",
        ),
    )


def record_stage_transition(
    state: ProjectState,
    item: ProjectWorkItem,
    *,
    stage_id: str,
    status: str,
    actor: str | None = None,
    origin: str | None = None,
    run_id: str | None = None,
    summary: str | None = None,
    save_target: str | None = None,
    validation_record_refs: tuple[str, ...] = (),
    metadata: dict[str, object] | None = None,
) -> ItemStageRecord:
    workflow = resolve_available_workflow(
        state.paths,
        item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    _resolve_stage(workflow, stage_id)
    record = append_item_stage_record(
        state.paths,
        item,
        stage_id=stage_id,
        status=status,
        actor=actor,
        origin=origin,
        run_id=run_id,
        summary=summary,
        save_target=save_target,
        validation_record_refs=validation_record_refs,
        metadata=metadata,
    )
    refreshed_state = ProjectState(
        paths=state.paths,
        config_overrides=load_project_config_overrides(state.paths),
        repos=state.repos,
        memories=state.memories,
        contexts=state.contexts,
        work_items=tuple(
            current
            if current.id != item.id
            else replace(current, workflow_id=workflow.workflow_id)
            for current in state.work_items
        ),
        recent_runs=state.recent_runs,
    )
    sync_item_workflow_fields(
        refreshed_state,
        replace(item, workflow_id=workflow.workflow_id),
    )
    return record


def _workflow_item_summary(
    state: ProjectState,
    item: ProjectWorkItem,
    *,
    workflow: WorkflowDefinition,
    item_lookup: dict[str, ProjectWorkItem],
) -> dict[str, object]:
    analysis = _analyze_item_workflow(state, item, workflow, item_lookup=item_lookup)
    workflow_state = analysis["workflow_state"]
    stages = analysis["stages"]
    next_stage = next(
        (
            stage
            for stage in stages
            if stage["stage_status"] in _ACTIONABLE_STAGE_STATUSES
        ),
        None,
    )
    blocked_by = list(workflow_state.blocking_reasons)
    if next_stage is not None:
        blocked_by = list(next_stage["blocked_by"])
    return {
        "item_ref": item.id,
        "item_slug": item.slug,
        "item_title": item.title,
        "item_status": item.status,
        "workflow_id": workflow.workflow_id,
        "current_stage_id": workflow_state.current_stage_id,
        "workflow_status": workflow_state.workflow_status,
        "stage_status": workflow_state.stage_status,
        "allowed_next_stages": list(workflow_state.allowed_next_stages),
        "pending_approvals": list(workflow_state.pending_approvals),
        "item_dependencies": list(item.depends_on),
        "next_artifact": next_stage["stage_id"] if next_stage is not None else None,
        "next_artifact_status": next_stage["summary_status"]
        if next_stage is not None
        else None,
        "blocked_by": blocked_by,
        "artifacts": stages,
        "stages": stages,
    }


def _analyze_item_workflow(
    state: ProjectState,
    item: ProjectWorkItem,
    workflow: WorkflowDefinition,
    *,
    item_lookup: dict[str, ProjectWorkItem] | None = None,
) -> dict[str, object]:
    validation_records = load_validation_records(state.paths)
    item_lookup = item_lookup or {current.id: current for current in state.work_items}
    records = [
        record
        for record in item_stage_records_for_paths(
            state.paths, item.id, workflow_id=workflow.workflow_id
        )
        if record.workflow_id == workflow.workflow_id
    ]
    latest_by_stage = {
        stage.stage_id: latest_stage_record_for_paths(
            state.paths,
            item.id,
            stage.stage_id,
            workflow_id=workflow.workflow_id,
        )
        for stage in workflow.stages
    }
    completed_stages: set[str] = set()
    stage_summaries: list[dict[str, object]] = []
    for stage in _ordered_stages(workflow):
        latest = latest_by_stage.get(stage.stage_id)
        blocked_by = _blocking_reasons_for_stage(
            item,
            stage,
            workflow,
            completed_stages=completed_stages,
            validation_records=validation_records,
            item_lookup=item_lookup,
        )
        complete = _stage_complete(
            state,
            item,
            stage,
            latest=latest,
            validation_records=validation_records,
        )
        stage_status = _stage_status_for_summary(
            latest, complete=complete, blocked_by=blocked_by
        )
        if complete:
            completed_stages.add(stage.stage_id)
        stage_summaries.append(
            {
                "name": stage.stage_id,
                "stage_id": stage.stage_id,
                "label": stage.label,
                "description": stage.output_kind,
                "kind": stage.kind,
                "order": stage.order,
                "memory_ref_field": _memory_ref_field_for_stage(stage),
                "memory_ref": _memory_ref_for_stage(item, stage),
                "depends_on": [
                    transition.from_stage
                    for transition in workflow.transitions
                    if transition.to_stage == stage.stage_id
                    and transition.from_stage is not None
                ],
                "status": stage_status
                if stage_status in _READY_STAGE_STATUSES
                else "blocked",
                "stage_status": stage_status,
                "summary_status": "ready"
                if stage_status in {"ready", "running"}
                else ("blocked" if blocked_by else stage_status),
                "blocked_by": blocked_by,
                "complete": complete,
                "allowed": stage_status == "ready",
                "requires_approval_before_entry": stage.requires_approval_before_entry,
                "allows_human_completion": stage.allows_human_completion,
                "allows_runtime_execution": stage.allows_runtime_execution,
                "output_kind": stage.output_kind,
                "save_target_rule": stage.save_target_rule,
                "validation_rule": stage.validation_rule,
                "instruction_template_id": stage.instruction_template_id,
                "latest_record": latest.to_dict() if latest is not None else None,
            }
        )
    workflow_state = _workflow_state_from_stage_summaries(
        item, workflow, stage_summaries
    )
    return {
        "workflow_state": workflow_state,
        "stages": stage_summaries,
        "records": records,
    }


def _workflow_state_from_stage_summaries(
    item: ProjectWorkItem,
    workflow: WorkflowDefinition,
    stage_summaries: list[dict[str, object]],
) -> ItemWorkflowState:
    if item.status in {"closed", "rejected"}:
        return ItemWorkflowState(
            item_ref=item.id,
            workflow_id=workflow.workflow_id,
            current_stage_id=None,
            workflow_status="closed",
            stage_status="succeeded",
            allowed_next_stages=(),
            blocking_reasons=(),
            pending_approvals=(),
        )
    allowed = tuple(
        stage["stage_id"]
        for stage in stage_summaries
        if stage["allowed"] and not stage["complete"]
    )
    blocking_reasons = tuple(
        dict.fromkeys(
            reason
            for stage in stage_summaries
            if not stage["complete"]
            for reason in stage["blocked_by"]
        )
    )
    pending_approvals = tuple(
        stage["stage_id"]
        for stage in stage_summaries
        if not stage["complete"] and "approval:item" in stage["blocked_by"]
    )
    current_stage = next(
        (
            stage
            for stage in stage_summaries
            if stage["stage_status"] in {"running", "failed", "needs_review"}
        ),
        None,
    )
    if current_stage is None:
        current_stage = next(
            (stage for stage in stage_summaries if not stage["complete"]), None
        )
    if current_stage is None:
        workflow_status: WorkflowStatus = "completed"
        stage_status: WorkflowStageStatus | None = "succeeded"
    elif current_stage["stage_status"] == "running":
        workflow_status = "in_progress"
        stage_status = "running"
    elif current_stage["stage_status"] in {"failed", "needs_review"}:
        workflow_status = "blocked"
        stage_status = current_stage["stage_status"]
    elif pending_approvals:
        workflow_status = "waiting_approval"
        stage_status = "not_started"
    elif allowed:
        workflow_status = "ready"
        stage_status = "ready"
    elif current_stage["stage_id"] in {"validate", "validate_summary"}:
        workflow_status = "waiting_validation"
        stage_status = "not_started"
    elif blocking_reasons:
        workflow_status = "blocked"
        stage_status = "not_started"
    else:
        workflow_status = "draft"
        stage_status = "not_started"
    return ItemWorkflowState(
        item_ref=item.id,
        workflow_id=workflow.workflow_id,
        current_stage_id=current_stage["stage_id"]
        if current_stage is not None
        else None,
        workflow_status=workflow_status,
        stage_status=stage_status,
        allowed_next_stages=allowed,
        blocking_reasons=blocking_reasons,
        pending_approvals=pending_approvals,
    )


def _blocking_reasons_for_stage(
    item: ProjectWorkItem,
    stage: WorkflowStageDefinition,
    workflow: WorkflowDefinition,
    *,
    completed_stages: set[str],
    validation_records: list[dict[str, object]],
    item_lookup: dict[str, ProjectWorkItem],
) -> list[str]:
    blocked_by = [
        f"item:{dependency}"
        for dependency in item.depends_on
        if dependency not in item_lookup
        or item_lookup[dependency].status not in _DONE_DEPENDENCY_STATUSES
    ]
    if stage.requires_approval_before_entry and not _approval_granted(item):
        blocked_by.append("approval:item")
    for transition in workflow.transitions:
        if transition.to_stage != stage.stage_id:
            continue
        if transition.rule == "create":
            continue
        if (
            transition.rule == "stage_succeeded"
            and transition.from_stage not in completed_stages
        ):
            if transition.from_stage is not None:
                blocked_by.append(f"stage:{transition.from_stage}")
        if transition.condition == "validation_exists" and not _validation_exists(
            item,
            validation_records,
        ):
            blocked_by.append("validation:item")
    if stage.validation_rule == "validation_record_required" and not _validation_exists(
        item,
        validation_records,
    ):
        blocked_by.append("validation:item")
    return list(dict.fromkeys(blocked_by))


def _stage_complete(
    state: ProjectState,
    item: ProjectWorkItem,
    stage: WorkflowStageDefinition,
    *,
    latest: ItemStageRecord | None,
    validation_records: list[dict[str, object]],
) -> bool:
    if latest is not None and latest.status == "succeeded":
        return True
    if stage.stage_id == "plan":
        return _memory_ref_has_content(state, item.plan_memory_ref) or item.status in {
            "planned",
            "in_progress",
            "implemented",
            "validated",
            "closed",
        }
    if stage.stage_id == "implement":
        return _memory_ref_has_content(
            state, item.implementation_memory_ref
        ) or item.status in {
            "implemented",
            "validated",
            "closed",
        }
    if stage.stage_id == "validate":
        return _validation_exists(item, validation_records)
    if stage.stage_id == "validate_summary":
        return _memory_ref_has_content(
            state, item.validation_memory_ref
        ) or item.status in {
            "validated",
            "closed",
        }
    return False


def _stage_status_for_summary(
    latest: ItemStageRecord | None,
    *,
    complete: bool,
    blocked_by: list[str],
) -> WorkflowStageStatus:
    if latest is not None and latest.status in {"running", "failed", "needs_review"}:
        return latest.status
    if complete:
        return "succeeded"
    if blocked_by:
        return "not_started"
    return "ready"


def _ordered_stages(
    workflow: WorkflowDefinition,
) -> tuple[WorkflowStageDefinition, ...]:
    return tuple(
        sorted(workflow.stages, key=lambda stage: (stage.order, stage.stage_id))
    )


def _ordered_artifact_rules(config: ProjectConfig) -> tuple[ProjectArtifactRule, ...]:
    rule_map = {rule.name: rule for rule in config.artifact_rules}
    if config.default_artifact_order:
        ordered = [
            rule_map[name] for name in config.default_artifact_order if name in rule_map
        ]
        seen = {rule.name for rule in ordered}
        ordered.extend(rule for rule in config.artifact_rules if rule.name not in seen)
        return tuple(ordered)
    return config.artifact_rules


def _resolve_stage(
    workflow: WorkflowDefinition, stage_id: str
) -> WorkflowStageDefinition:
    for stage in workflow.stages:
        if stage.stage_id == stage_id:
            return stage
    raise LaunchError(
        f"Workflow {workflow.workflow_id} does not define stage {stage_id}."
    )


def _artifact_rules_for_summary(
    config: ProjectConfig,
    workflow: WorkflowDefinition,
) -> tuple[ProjectArtifactRule, ...]:
    if config.artifact_rules:
        return config.artifact_rules
    return tuple(
        ProjectArtifactRule(
            name=stage.stage_id,
            depends_on=tuple(
                transition.from_stage
                for transition in workflow.transitions
                if transition.to_stage == stage.stage_id
                and transition.from_stage is not None
            ),
            memory_ref_field=_memory_ref_field_for_stage(stage),
            label=stage.label,
            description=stage.output_kind,
        )
        for stage in _ordered_stages(workflow)
    )


def _memory_ref_field_for_stage(stage: WorkflowStageDefinition) -> str | None:
    mapping = {
        "item_plan_memory": "plan_memory_ref",
        "item_implementation_memory": "implementation_memory_ref",
        "validation_summary_memory": "validation_memory_ref",
    }
    return mapping.get(stage.save_target_rule or "")


def _memory_ref_for_stage(
    item: ProjectWorkItem, stage: WorkflowStageDefinition
) -> str | None:
    field = _memory_ref_field_for_stage(stage)
    if field is None:
        return None
    value = getattr(item, field, None)
    return value if isinstance(value, str) else None


def _resolve_save_target(
    item: ProjectWorkItem, stage: WorkflowStageDefinition
) -> str | None:
    if stage.save_target_rule == "item_plan_memory":
        return item.plan_memory_ref
    if stage.save_target_rule == "item_implementation_memory":
        return item.implementation_memory_ref
    if stage.save_target_rule == "validation_summary_memory":
        return item.validation_memory_ref
    if stage.save_target_rule == "validation_record":
        return f"validation:{item.id}"
    return item.save_target_ref


def _prompt_seed_for_stage(item: ProjectWorkItem, stage_id: str) -> str:
    if stage_id == "plan":
        return default_item_plan_prompt(item)
    headline = f"{item.title}\n\n{item.description}".strip()
    if stage_id == "implement":
        return f"Implement the approved plan for:\n\n{headline}"
    if stage_id == "validate":
        return f"Validate the implementation for:\n\n{headline}"
    if stage_id == "validate_summary":
        return f"Summarize the validation findings for:\n\n{headline}"
    return headline


def _approval_granted(item: ProjectWorkItem) -> bool:
    return bool(
        item.approved_at
        or item.status
        in {"approved", "in_progress", "implemented", "validated", "closed"}
    )


def _validation_exists(
    item: ProjectWorkItem,
    validation_records: list[dict[str, object]],
) -> bool:
    if item.status in {"validated", "closed"}:
        return True
    return any(
        record.get("project_item_ref") == item.id for record in validation_records
    )


def _legacy_status_and_stage(
    item: ProjectWorkItem,
    workflow_state: ItemWorkflowState,
) -> tuple[str, str]:
    if item.status in {"closed", "rejected"}:
        return item.status, "closure"
    if workflow_state.current_stage_id == "plan":
        if workflow_state.stage_status == "succeeded":
            return "planned", "planning"
        return "approved", "planning"
    if workflow_state.current_stage_id == "implement":
        if workflow_state.stage_status == "succeeded":
            return "implemented", "execution"
        return "in_progress", "execution"
    if workflow_state.current_stage_id == "validate":
        if workflow_state.stage_status == "succeeded":
            return "validated", "validation"
        return "implemented", "validation"
    if workflow_state.current_stage_id == "validate_summary":
        return "validated", "validation"
    if workflow_state.workflow_status == "waiting_approval":
        return "draft", "approval"
    if workflow_state.workflow_status in {"completed", "closed"}:
        return "validated", "validation"
    return item.status, item.stage


def _memory_ref_has_content(state: ProjectState, ref: str | None) -> bool:
    if ref is None:
        return False
    memory = next((entry for entry in state.memories if entry.id == ref), None)
    if memory is None:
        return False
    path = state.paths.project_dir / memory.path
    if not path.exists():
        return False
    return bool(path.read_text(encoding="utf-8").strip())


def _request_ids_for_paths(paths: ProjectPaths) -> list[str]:
    request_ids: list[str] = []
    for record in load_stage_records(paths):
        metadata = record.metadata or {}
        request_id = metadata.get("request_id")
        if isinstance(request_id, str):
            request_ids.append(request_id)
    return request_ids


def _legacy_memory_completion_state(state: ProjectState) -> dict[str, bool]:
    return {
        memory.id: _memory_ref_has_content(state, memory.id)
        for memory in state.memories
    }


def _legacy_item_workflow_state(
    item: ProjectWorkItem,
    *,
    rules: tuple[ProjectArtifactRule, ...],
    item_lookup: dict[str, ProjectWorkItem],
    memory_state: dict[str, bool],
) -> dict[str, object]:
    if item.status in {"closed", "rejected"}:
        workflow_status = "done"
        next_artifact = None
        next_artifact_status = None
        blocked_by: list[str] = []
        artifact_states = [
            {
                "name": rule.name,
                "label": rule.label,
                "description": rule.description,
                "memory_ref_field": rule.memory_ref_field,
                "memory_ref": _memory_ref_for_rule(item, rule),
                "depends_on": list(rule.depends_on),
                "status": "done",
                "blocked_by": [],
                "complete": True,
                "stage_status": "succeeded",
                "summary_status": "done",
                "allowed": False,
            }
            for rule in rules
        ]
    else:
        unresolved_dependencies = [
            dependency
            for dependency in item.depends_on
            if dependency not in item_lookup
            or item_lookup[dependency].status not in _DONE_DEPENDENCY_STATUSES
        ]
        artifact_states, next_artifact, next_artifact_status, blocked_by = (
            _legacy_artifact_states_for_item(
                item,
                rules=rules,
                memory_state=memory_state,
                unresolved_dependencies=unresolved_dependencies,
            )
        )
        workflow_status = "blocked" if next_artifact_status == "blocked" else "ready"
    return {
        "item_ref": item.id,
        "item_slug": item.slug,
        "item_title": item.title,
        "item_status": item.status,
        "workflow_status": workflow_status,
        "item_dependencies": list(item.depends_on),
        "next_artifact": next_artifact,
        "next_artifact_status": next_artifact_status,
        "blocked_by": blocked_by,
        "artifacts": artifact_states,
        "stages": artifact_states,
    }


def _legacy_artifact_states_for_item(
    item: ProjectWorkItem,
    *,
    rules: tuple[ProjectArtifactRule, ...],
    memory_state: dict[str, bool],
    unresolved_dependencies: list[str],
) -> tuple[list[dict[str, object]], str | None, str | None, list[str]]:
    states: list[dict[str, object]] = []
    done_rules: set[str] = set()
    next_artifact: str | None = None
    next_artifact_status: str | None = None
    next_blocked_by: list[str] = []
    for rule in rules:
        memory_ref = _memory_ref_for_rule(item, rule)
        complete = bool(memory_ref) and memory_state.get(memory_ref, False)
        blocked_by = [f"item:{ref}" for ref in unresolved_dependencies]
        blocked_by.extend(
            f"artifact:{dependency}"
            for dependency in rule.depends_on
            if dependency not in done_rules
        )
        if complete:
            status = "done"
            done_rules.add(rule.name)
        elif blocked_by:
            status = "blocked"
        else:
            status = "ready"
        states.append(
            {
                "name": rule.name,
                "label": rule.label,
                "description": rule.description,
                "memory_ref_field": rule.memory_ref_field,
                "memory_ref": memory_ref,
                "depends_on": list(rule.depends_on),
                "status": status,
                "blocked_by": blocked_by,
                "complete": complete,
                "stage_status": "succeeded" if complete else "not_started",
                "summary_status": status,
                "allowed": status == "ready",
            }
        )
        if next_artifact is None and not complete:
            next_artifact = rule.name
            next_artifact_status = status
            next_blocked_by = blocked_by
    return states, next_artifact, next_artifact_status, next_blocked_by


def _memory_ref_for_rule(
    item: ProjectWorkItem,
    rule: ProjectArtifactRule,
) -> str | None:
    if rule.memory_ref_field is None:
        return None
    value = getattr(item, rule.memory_ref_field, None)
    return value if isinstance(value, str) else None


def _item_sort_key(item_state: dict[str, object]) -> tuple[int, str, str]:
    rank_order = (
        "draft",
        "planned",
        "approved",
        "in_progress",
        "implemented",
        "validated",
        "closed",
        "rejected",
    )
    status = item_state.get("item_status")
    if not isinstance(status, str):
        status = "rejected"
    try:
        rank = rank_order.index(status)
    except ValueError:
        rank = len(rank_order)
    item_ref = item_state.get("item_ref")
    item_slug = item_state.get("item_slug")
    return (
        rank,
        item_ref if isinstance(item_ref, str) else "",
        item_slug if isinstance(item_slug, str) else "",
    )


def build_expanded_execution_request(
    request: ExecutionRequest,
    *,
    final_prompt: str,
    composed_prompt: str,
    sources: tuple[dict[str, object], ...],
    repo_refs: tuple[str, ...],
    run_in_repo: str | None,
    save_target: str | None,
    save_mode: MemoryUpdateMode | None,
    source_summary: dict[str, object],
    context_hash: str | None,
    warnings: tuple[str, ...],
) -> ExpandedExecutionRequest:
    return ExpandedExecutionRequest(
        request=request,
        final_prompt=final_prompt,
        composed_prompt=composed_prompt,
        sources=sources,
        repo_refs=repo_refs,
        run_in_repo=run_in_repo,
        save_target=save_target,
        save_mode=save_mode,
        source_summary=source_summary,
        context_hash=context_hash,
        warnings=warnings,
    )


def execution_outcome_summary(text: str | None) -> str | None:
    if text is None:
        return None
    return summarize_text(text)
