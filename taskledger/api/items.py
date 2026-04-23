from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.api.types import ItemDossier, ItemDossierSection, Memory, WorkItem
from taskledger.api.workflows import mark_stage_running, mark_stage_succeeded
from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths, utc_now_iso
from taskledger.storage import (
    create_memory,
    create_work_item,
    delete_memory,
    load_contexts,
    load_project_state,
    load_run_records,
    load_validation_records,
    load_work_items,
    read_memory_body,
    refresh_memory,
    rename_memory,
    resolve_memory,
    resolve_work_item,
    update_memory_body,
    update_memory_tags,
    update_work_item,
    write_memory_body,
)
from taskledger.storage.common import summarize_text
from taskledger.workflow import (
    default_workflow_id_for_paths,
    item_stage_records_for_paths,
    item_workflow_state_payload,
)

_ITEM_MEMORY_ROLE_FIELDS = {
    "analysis": "analysis_memory_ref",
    "current": "state_memory_ref",
    "plan": "plan_memory_ref",
    "implementation": "implementation_memory_ref",
    "validation": "validation_memory_ref",
    "save_target": "save_target_ref",
}
_ITEM_MEMORY_ROLE_ALIASES = {"state": "current"}

_DEFAULT_DOSSIER_ROLES = (
    "analysis",
    "current",
    "plan",
    "implementation",
    "validation",
)

_ITEM_MEMORY_ROLE_TITLES = {
    "analysis": "Analysis",
    "current": "Current State",
    "plan": "Plan",
    "implementation": "Implementation",
    "validation": "Validation",
    "save_target": "Save Target",
}
_ACTIONABLE_STAGE_STATUSES = {"ready", "running", "failed", "needs_review"}
_STAGE_ROLE_BY_STAGE_ID = {
    "plan": "plan",
    "implement": "implementation",
    "validate": "validation",
    "validate_summary": "validation",
}
_STAGE_ROLE_BY_KIND = {
    "analysis": "analysis",
    "implementation": "implementation",
    "validation": "validation",
    "summary": "validation",
}


def create_item(
    workspace_root: Path,
    *,
    slug: str,
    description: str,
    repo_refs: tuple[str, ...] = (),
    source_path: Path | None = None,
    title: str | None = None,
    target_repo_ref: str | None = None,
) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    workflow_id = default_workflow_id_for_paths(paths)
    normalized_slug = slug.strip()
    if not normalized_slug:
        raise LaunchError("Project work item slug must not be empty.")
    return create_work_item(
        paths,
        slug=normalized_slug,
        title=title or _title_from_slug(normalized_slug),
        description=description,
        source_path=source_path,
        repo_refs=repo_refs,
        target_repo_ref=target_repo_ref,
        workflow_id=workflow_id,
        workflow_status="draft",
        stage_status="not_started",
    )


def list_items(workspace_root: Path) -> list[WorkItem]:
    return load_work_items(load_project_state(workspace_root).paths)


def show_item(workspace_root: Path, ref: str) -> WorkItem:
    return resolve_work_item(load_project_state(workspace_root).paths, ref)


def approve_item(workspace_root: Path, ref: str) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)
    return update_work_item(paths, ref, _approve_item(paths, item))


def reopen_item(workspace_root: Path, ref: str) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)
    return update_work_item(paths, ref, _reopen_item(paths, item))


def close_item(workspace_root: Path, ref: str) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)
    return update_work_item(paths, ref, _close_item(item))


def item_memory_refs(workspace_root: Path, item_ref: str) -> dict[str, str | None]:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, item_ref)
    return _memory_refs_for_item(item)


def resolve_item_memory(workspace_root: Path, item_ref: str, role: str) -> Memory:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, item_ref)
    normalized_role = _canonical_item_memory_role(role)
    field_name = _memory_field_for_role(normalized_role)
    memory_ref = getattr(item, field_name)
    if not memory_ref:
        raise LaunchError(
            f"Work item {item.slug} has no memory for role {normalized_role} yet."
        )
    try:
        return resolve_memory(paths, memory_ref)
    except LaunchError as exc:
        raise LaunchError(
            f"Work item {item.slug} has an invalid {normalized_role} memory ref: "
            f"{memory_ref}"
        ) from exc


def read_item_memory_body(workspace_root: Path, item_ref: str, role: str) -> str:
    paths = load_project_state(workspace_root).paths
    memory = resolve_item_memory(workspace_root, item_ref, role)
    return read_memory_body(paths, memory)


def write_item_memory_body(
    workspace_root: Path,
    item_ref: str,
    role: str,
    text: str,
    *,
    mode: str = "replace",
) -> Memory:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, item_ref)
    normalized_role = _canonical_item_memory_role(role)
    field_name = _memory_field_for_role(normalized_role)
    existing_ref = getattr(item, field_name)
    if not text.strip():
        if existing_ref is None:
            raise LaunchError(
                f"Work item {item.slug} has no memory for role {normalized_role} yet."
            )
        if mode in {"append", "prepend"}:
            return resolve_item_memory(workspace_root, item_ref, normalized_role)
    if existing_ref is None:
        memory = _create_item_memory(
            paths,
            item,
            role=normalized_role,
            body=text,
        )
        if mode in {"replace", "append", "prepend"}:
            return memory
        raise LaunchError(f"Unsupported item memory write mode: {mode}")
    memory = resolve_item_memory(workspace_root, item_ref, normalized_role)
    if mode == "replace":
        return write_memory_body(paths, memory.id, text)
    if mode in {"append", "prepend"}:
        return update_memory_body(paths, memory.id, text, mode=mode)
    raise LaunchError(f"Unsupported item memory write mode: {mode}")


def rename_item_memory(
    workspace_root: Path,
    item_ref: str,
    role: str,
    *,
    new_name: str,
) -> Memory:
    paths = load_project_state(workspace_root).paths
    memory = resolve_item_memory(workspace_root, item_ref, role)
    return rename_memory(paths, memory.id, new_name)


def retag_item_memory(
    workspace_root: Path,
    item_ref: str,
    role: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> Memory:
    paths = load_project_state(workspace_root).paths
    memory = resolve_item_memory(workspace_root, item_ref, role)
    return update_memory_tags(
        paths,
        memory.id,
        add_tags=add_tags,
        remove_tags=remove_tags,
    )


def delete_item_memory(workspace_root: Path, item_ref: str, role: str) -> Memory:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, item_ref)
    memory = resolve_item_memory(workspace_root, item_ref, role)
    deleted = delete_memory(paths, memory.id)
    updated_item = _drop_memory_refs(item, memory.id)
    update_work_item(paths, item.id, updated_item)
    return deleted


def update_item(
    workspace_root: Path,
    ref: str,
    *,
    title: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    owner: str | None = None,
    estimate: str | None = None,
    add_labels: tuple[str, ...] = (),
    remove_labels: tuple[str, ...] = (),
    add_dependencies: tuple[str, ...] = (),
    remove_dependencies: tuple[str, ...] = (),
    add_repo_refs: tuple[str, ...] = (),
    remove_repo_refs: tuple[str, ...] = (),
    target_repo_ref: str | None = None,
    add_acceptance: tuple[str, ...] = (),
    remove_acceptance: tuple[str, ...] = (),
    add_validation_checks: tuple[str, ...] = (),
    remove_validation_checks: tuple[str, ...] = (),
    save_target_ref: str | None = None,
) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)

    normalized_title = _normalize_optional_text(title, field_name="title")
    normalized_description = _normalize_optional_text(
        description,
        field_name="description",
    )
    normalized_notes = _normalize_optional_text(notes, field_name="notes")
    normalized_owner = _normalize_optional_text(owner, field_name="owner")
    normalized_estimate = _normalize_optional_text(estimate, field_name="estimate")
    normalized_target_repo = _normalize_optional_text(
        target_repo_ref,
        field_name="target_repo",
    )
    normalized_save_target = _normalize_optional_text(
        save_target_ref,
        field_name="save_target",
    )

    labels = _apply_sequence_patch(
        item.labels,
        _normalize_text_values(add_labels, field_name="label"),
        _normalize_text_values(remove_labels, field_name="label"),
        field_name="label",
    )
    dependencies = _apply_sequence_patch(
        item.depends_on,
        _normalize_text_values(add_dependencies, field_name="dependency"),
        _normalize_text_values(remove_dependencies, field_name="dependency"),
        field_name="dependency",
    )
    repo_refs = _apply_sequence_patch(
        item.repo_refs,
        _normalize_text_values(add_repo_refs, field_name="repo"),
        _normalize_text_values(remove_repo_refs, field_name="repo"),
        field_name="repo",
    )
    acceptance_criteria = _apply_sequence_patch(
        item.acceptance_criteria,
        _normalize_text_values(add_acceptance, field_name="acceptance criteria"),
        _normalize_text_values(remove_acceptance, field_name="acceptance criteria"),
        field_name="acceptance criteria",
    )
    validation_checklist = _apply_sequence_patch(
        item.validation_checklist,
        _normalize_text_values(
            add_validation_checks,
            field_name="validation checklist item",
        ),
        _normalize_text_values(
            remove_validation_checks,
            field_name="validation checklist item",
        ),
        field_name="validation checklist item",
    )

    updated = replace(
        item,
        title=normalized_title or item.title,
        description=normalized_description or item.description,
        notes=normalized_notes if normalized_notes is not None else item.notes,
        owner=normalized_owner if normalized_owner is not None else item.owner,
        estimate=(
            normalized_estimate if normalized_estimate is not None else item.estimate
        ),
        labels=labels,
        depends_on=dependencies,
        repo_refs=repo_refs,
        target_repo_ref=(
            normalized_target_repo
            if normalized_target_repo is not None
            else item.target_repo_ref
        ),
        acceptance_criteria=acceptance_criteria,
        validation_checklist=validation_checklist,
        save_target_ref=(
            normalized_save_target
            if normalized_save_target is not None
            else item.save_target_ref
        ),
    )
    if updated == item:
        raise LaunchError("No item updates requested.")
    return update_work_item(paths, ref, updated)


def item_summary(workspace_root: Path, item_ref: str) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    return _item_summary_payload(state, item)


def build_item_work_prompt(
    workspace_root: Path,
    item_ref: str,
    *,
    stage_id: str | None = None,
) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    workflow_payload = item_workflow_state_payload(state, item)
    stage_detail = _resolve_summary_stage(workflow_payload, stage_id=stage_id)
    state_payload = workflow_payload.get("state")
    state_payload = state_payload if isinstance(state_payload, dict) else {}
    if stage_detail is None:
        return {
            "item_ref": item.slug,
            "item_id": item.id,
            "stage": state_payload.get("current_stage_id"),
            "target_repo_ref": item.target_repo_ref,
            "save_target_ref": item.save_target_ref,
            "suggested_memory_role": None,
            "context_refs": _referencing_context_refs(state.paths, item),
            "blocked_by": list(state_payload.get("blocking_reasons", ()))
            if isinstance(state_payload.get("blocking_reasons"), list)
            else [],
            "prompt": (
                f"Review completed Taskledger item {item.slug} ({item.id}) and capture "
                "any final context worth preserving."
            ),
        }
    suggested_memory_role = _memory_role_for_stage_detail(stage_detail)
    save_target_ref = _save_target_ref_for_stage(item, stage_detail)
    blocked_by = _stage_blocked_by(stage_detail)
    prompt = _build_work_prompt_text(
        item,
        stage_detail=stage_detail,
        target_repo_ref=item.target_repo_ref,
        save_target_ref=save_target_ref,
        suggested_memory_role=suggested_memory_role,
        blocked_by=blocked_by,
    )
    return {
        "item_ref": item.slug,
        "item_id": item.id,
        "stage": str(stage_detail["stage_id"]),
        "target_repo_ref": item.target_repo_ref,
        "save_target_ref": save_target_ref,
        "suggested_memory_role": suggested_memory_role,
        "context_refs": _referencing_context_refs(state.paths, item),
        "blocked_by": blocked_by,
        "prompt": prompt,
    }


def start_item_work(
    workspace_root: Path,
    item_ref: str,
    *,
    mark_running: bool = False,
    stage_id: str | None = None,
) -> dict[str, object]:
    prompt_payload = build_item_work_prompt(
        workspace_root,
        item_ref,
        stage_id=stage_id,
    )
    marked_running = False
    if mark_running:
        state = load_project_state(workspace_root, recent_runs_limit=0)
        item = resolve_work_item(state.paths, item_ref)
        workflow_payload = item_workflow_state_payload(state, item)
        stage_detail = _resolve_summary_stage(
            workflow_payload,
            stage_id=str(prompt_payload["stage"]),
        )
        stage_status = str(stage_detail.get("stage_status") or "not_started")
        if stage_status == "running":
            marked_running = False
        elif stage_status in {"ready", "failed", "needs_review"}:
            mark_stage_running(workspace_root, item.id, str(stage_detail["stage_id"]))
            marked_running = True
        else:
            blocked_by = _stage_blocked_by(stage_detail)
            reason = ", ".join(blocked_by) if blocked_by else stage_status
            raise LaunchError(
                f"Stage {stage_detail['stage_id']} cannot be marked running: {reason}"
            )

    summary = item_summary(workspace_root, item_ref)
    prompt_payload = build_item_work_prompt(
        workspace_root,
        item_ref,
        stage_id=str(prompt_payload["stage"]),
    )
    item_payload = summary["item"]
    assert isinstance(item_payload, dict)
    next_action = summary["next_action"]
    memories = summary["memories"]
    return {
        "item": item_payload,
        "workflow": {
            "workflow_id": item_payload["workflow_id"],
            "current_stage": prompt_payload["stage"],
            "marked_running": marked_running,
            "blocked_by": prompt_payload["blocked_by"],
        },
        "next_action": next_action,
        "target_repo_ref": prompt_payload["target_repo_ref"],
        "save_target_ref": prompt_payload["save_target_ref"],
        "memories": memories,
        "context_refs": prompt_payload["context_refs"],
        "prompt": prompt_payload["prompt"],
    }


def complete_item_stage(
    workspace_root: Path,
    item_ref: str,
    *,
    stage_id: str,
    run_refs: tuple[str, ...] = (),
    validation_refs: tuple[str, ...] = (),
    summary: str | None = None,
) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    workflow_payload = item_workflow_state_payload(state, item)
    stage_detail = _resolve_summary_stage(workflow_payload, stage_id=stage_id)
    _ensure_stage_can_complete(stage_detail)

    normalized_run_refs = tuple(
        show["id"]
        for show in _resolved_run_payloads(workspace_root, run_refs)
    )
    normalized_validation_refs = _resolved_validation_refs(
        workspace_root,
        validation_refs,
    )
    item = _attach_run_refs_to_item(state.paths, item, normalized_run_refs)
    save_target_ref = _save_target_ref_for_stage(item, stage_detail)
    mark_stage_succeeded(
        workspace_root,
        item.id,
        stage_id,
        run_id=normalized_run_refs[0] if normalized_run_refs else None,
        summary=summary,
        save_target=save_target_ref,
        validation_record_refs=normalized_validation_refs,
    )
    updated_summary = item_summary(workspace_root, item.id)
    refreshed_state = load_project_state(workspace_root, recent_runs_limit=0)
    refreshed_item = resolve_work_item(refreshed_state.paths, item.id)
    workflow_payload = item_workflow_state_payload(refreshed_state, refreshed_item)
    state_payload = workflow_payload.get("state")
    assert isinstance(state_payload, dict)
    workflow_state = {
        "current_stage": state_payload.get("current_stage_id"),
        "status": state_payload.get("workflow_status"),
    }
    return {
        "item_ref": item.slug,
        "completed_stage": stage_id,
        "attached_run_refs": list(normalized_run_refs),
        "attached_validation_refs": list(normalized_validation_refs),
        "workflow": workflow_state,
        "item": updated_summary["item"],
    }


def refine_item(
    workspace_root: Path,
    item_ref: str,
    *,
    title: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    acceptance_criteria: tuple[str, ...] | None = None,
    add_acceptance: tuple[str, ...] = (),
    validation_checks: tuple[str, ...] | None = None,
    add_validation_checks: tuple[str, ...] = (),
    repo_refs: tuple[str, ...] | None = None,
    add_repo_refs: tuple[str, ...] = (),
    target_repo_ref: str | None = None,
) -> dict[str, object]:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, item_ref)
    updated_fields: list[str] = []

    normalized_title = _normalize_optional_text(title, field_name="title")
    normalized_description = _normalize_optional_text(
        description,
        field_name="description",
    )
    normalized_notes = _normalize_optional_text(notes, field_name="notes")
    normalized_target_repo = _normalize_optional_text(
        target_repo_ref,
        field_name="target_repo",
    )

    next_acceptance = (
        _normalize_text_values(
            acceptance_criteria,
            field_name="acceptance criteria",
        )
        if acceptance_criteria is not None
        else _apply_sequence_patch(
            item.acceptance_criteria,
            _normalize_text_values(add_acceptance, field_name="acceptance criteria"),
            (),
            field_name="acceptance criteria",
        )
    )
    next_validation = (
        _normalize_text_values(
            validation_checks,
            field_name="validation checklist item",
        )
        if validation_checks is not None
        else _apply_sequence_patch(
            item.validation_checklist,
            _normalize_text_values(
                add_validation_checks,
                field_name="validation checklist item",
            ),
            (),
            field_name="validation checklist item",
        )
    )
    next_repo_refs = (
        _normalize_text_values(repo_refs, field_name="repo")
        if repo_refs is not None
        else _apply_sequence_patch(
            item.repo_refs,
            _normalize_text_values(add_repo_refs, field_name="repo"),
            (),
            field_name="repo",
        )
    )

    updated = replace(
        item,
        title=normalized_title or item.title,
        description=normalized_description or item.description,
        notes=normalized_notes if normalized_notes is not None else item.notes,
        acceptance_criteria=next_acceptance,
        validation_checklist=next_validation,
        repo_refs=next_repo_refs,
        target_repo_ref=(
            normalized_target_repo
            if normalized_target_repo is not None
            else item.target_repo_ref
        ),
    )
    if updated == item:
        raise LaunchError("No item refinements requested.")
    if updated.title != item.title:
        updated_fields.append("title")
    if updated.description != item.description:
        updated_fields.append("description")
    if updated.notes != item.notes:
        updated_fields.append("notes")
    if updated.acceptance_criteria != item.acceptance_criteria:
        updated_fields.append("acceptance_criteria")
    if updated.validation_checklist != item.validation_checklist:
        updated_fields.append("validation_checks")
    if updated.repo_refs != item.repo_refs:
        updated_fields.append("repo_refs")
    if updated.target_repo_ref != item.target_repo_ref:
        updated_fields.append("target_repo_ref")

    saved = update_work_item(paths, item.id, updated)
    payload = item_summary(workspace_root, saved.id)
    payload["updated_fields"] = updated_fields
    return payload


def item_dossier(
    workspace_root: Path,
    item_ref: str,
    *,
    roles: tuple[str, ...] | None = None,
    include_empty: bool = False,
    include_runs: bool = True,
    include_validation: bool = True,
    include_workflow: bool = True,
    include_contexts: bool = True,
) -> ItemDossier:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    selected_roles = _normalize_dossier_roles(roles)
    memory_refs = _memory_refs_for_item(item)
    stage_records = item_stage_records_for_paths(
        state.paths,
        item.id,
        workflow_id=item.workflow_id or default_workflow_id_for_paths(state.paths),
    )

    sections: list[ItemDossierSection] = []
    sections.append(_item_header_section(item))
    sections.append(
        ItemDossierSection(
            kind="description",
            title="Description",
            ref=item.id,
            body=item.description.strip(),
        )
    )
    sections.append(
        _list_section(
            kind="acceptance_criteria",
            title="Acceptance Criteria",
            values=item.acceptance_criteria,
        )
    )
    sections.append(
        _list_section(
            kind="validation_checklist",
            title="Validation Checklist",
            values=item.validation_checklist,
        )
    )
    sections.append(_item_details_section(item))
    sections.append(_memory_overview_section(item, memory_refs))
    for role in selected_roles:
        memory_section = _memory_body_section(
            state.paths,
            item,
            role=role,
            memory_ref=memory_refs.get(role),
            include_empty=include_empty,
        )
        if memory_section is not None:
            sections.append(memory_section)

    if include_workflow:
        workflow_payload = item_workflow_state_payload(state, item)
        sections.extend(
            _workflow_sections(
                workflow_payload=workflow_payload,
                stage_records=stage_records,
            )
        )
    if include_runs:
        sections.append(_runs_section(state.paths, item, stage_records=stage_records))
    if include_validation:
        sections.append(
            _validation_section(
                state.paths,
                item,
                stage_records=stage_records,
            )
        )
    if include_contexts:
        sections.append(_referencing_contexts_section(state.paths, item))

    dossier_sections = tuple(
        section
        for section in sections
        if section.body.strip() or section.kind in {"header", "memory_overview"}
    )
    metadata = {
        "item": item.to_dict(),
        "memory_refs": memory_refs,
        "selected_roles": list(selected_roles),
        "include_empty": include_empty,
        "include_runs": include_runs,
        "include_validation": include_validation,
        "include_workflow": include_workflow,
        "include_contexts": include_contexts,
        "stage_record_count": len(stage_records),
    }
    return ItemDossier(
        item_ref=item.id,
        title=item.title,
        sections=dossier_sections,
        metadata=metadata,
    )


def render_item_dossier_markdown(dossier: ItemDossier) -> str:
    lines: list[str] = []
    for section in dossier.sections:
        lines.append(section.title)
        lines.append(section.body.rstrip() if section.body.strip() else "(empty)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def next_action_payload(item: WorkItem) -> dict[str, object]:
    if item.status == "draft":
        action = "plan"
        actor = "runtime"
        reason = "The item is still in intake and needs a proposed plan."
    elif item.status == "planned":
        action = "approve"
        actor = "human"
        reason = "The plan exists but has not been approved for execution."
    elif item.status == "approved":
        action = "implement"
        actor = "runtime"
        reason = "The approved item is ready for implementation."
    elif item.status in {"in_progress", "implemented"}:
        action = "validate"
        actor = "runtime_or_human"
        reason = "Execution evidence exists and the next step is validation."
    elif item.status == "validated":
        action = "close"
        actor = "human"
        reason = "Validation is complete and the item can be closed."
    elif item.status == "closed":
        action = "inspect"
        actor = "human"
        reason = "The item is already closed."
    else:
        action = "inspect"
        actor = "human"
        reason = "Inspect the item before choosing the next action."
    return {
        "kind": "project_item_next",
        "item_ref": item.id,
        "action": action,
        "actor": actor,
        "reason": reason,
    }


def _normalize_dossier_roles(roles: tuple[str, ...] | None) -> tuple[str, ...]:
    if roles is None:
        return _DEFAULT_DOSSIER_ROLES
    normalized: list[str] = []
    for role in roles:
        candidate = _canonical_item_memory_role(role)
        _memory_field_for_role(candidate)
        if candidate in normalized:
            continue
        normalized.append(candidate)
    return tuple(normalized)


def _item_header_section(item: WorkItem) -> ItemDossierSection:
    body = _kv_block(
        [
            ("slug", item.slug),
            ("item_id", item.id),
            ("title", item.title),
            ("status", item.status),
            ("stage", item.stage),
            ("workflow_id", item.workflow_id),
            ("workflow_status", item.workflow_status),
            ("current_stage", item.current_stage_id),
            ("target_repo", item.target_repo_ref),
            ("save_target_ref", item.save_target_ref),
        ]
    )
    return ItemDossierSection(
        kind="header",
        title=f"ITEM DOSSIER {item.slug} ({item.id})",
        ref=item.id,
        body=body,
    )


def _item_details_section(item: WorkItem) -> ItemDossierSection:
    body = _kv_block(
        [
            ("labels", ", ".join(item.labels) or "(none)"),
            ("dependencies", ", ".join(item.depends_on) or "(none)"),
            ("notes", item.notes or "(none)"),
            ("owner", item.owner or "(none)"),
            ("estimate", item.estimate or "(none)"),
            ("linked_memories", ", ".join(item.linked_memories) or "(none)"),
            ("linked_runs", ", ".join(item.linked_runs) or "(none)"),
            ("linked_loop_tasks", ", ".join(item.linked_loop_tasks) or "(none)"),
        ]
    )
    return ItemDossierSection(
        kind="details",
        title="Item Details",
        ref=item.id,
        body=body,
    )


def _memory_overview_section(
    item: WorkItem,
    memory_refs: dict[str, str | None],
) -> ItemDossierSection:
    body = _kv_block(
        [
            (
                role,
                memory_refs.get(role) or "(none)",
            )
            for role in _ITEM_MEMORY_ROLE_FIELDS
        ]
    )
    return ItemDossierSection(
        kind="memory_overview",
        title="Memory Overview",
        ref=item.id,
        body=body,
    )


def _memory_body_section(
    paths,
    item: WorkItem,
    *,
    role: str,
    memory_ref: str | None,
    include_empty: bool,
) -> ItemDossierSection | None:
    if memory_ref is None:
        if not include_empty:
            return None
        return ItemDossierSection(
            kind="memory_body",
            title=_ITEM_MEMORY_ROLE_TITLES[role],
            ref=None,
            body="(empty)",
            metadata={"role": role, "memory_ref": None},
        )
    try:
        memory = resolve_memory(paths, memory_ref)
        body = read_memory_body(paths, memory).rstrip()
    except LaunchError as exc:
        body = f"(missing memory: {memory_ref}; {exc})"
        return ItemDossierSection(
            kind="memory_body",
            title=_ITEM_MEMORY_ROLE_TITLES[role],
            ref=memory_ref,
            body=body,
            metadata={"role": role, "memory_ref": memory_ref, "missing": True},
        )
    if not body:
        if not include_empty:
            return None
        body = "(empty)"
    return ItemDossierSection(
        kind="memory_body",
        title=_ITEM_MEMORY_ROLE_TITLES[role],
        ref=memory.id,
        body=body,
        metadata={
            "role": role,
            "memory_ref": memory.id,
            "memory_name": memory.name,
            "memory_slug": memory.slug,
        },
    )


def _workflow_sections(
    *,
    workflow_payload: dict[str, object],
    stage_records: list,
) -> tuple[ItemDossierSection, ItemDossierSection]:
    workflow = workflow_payload.get("workflow")
    state = workflow_payload.get("state")
    stages = workflow_payload.get("stages")
    assert isinstance(workflow, dict)
    assert isinstance(state, dict)
    assert isinstance(stages, list)
    next_stage = next(
        (
            stage
            for stage in stages
            if isinstance(stage, dict) and stage.get("complete") is False
        ),
        None,
    )
    blocked_by: list[str] = []
    if next_stage is not None and isinstance(next_stage.get("blocked_by"), list):
        blocked_by = [str(item) for item in next_stage.get("blocked_by", ())]
    elif isinstance(state.get("blocking_reasons"), list):
        blocked_by = [str(item) for item in state.get("blocking_reasons", ())]
    workflow_body = _kv_block(
        [
            (
                "workflow_id",
                str(state.get("workflow_id") or workflow.get("workflow_id")),
            ),
            ("workflow_status", str(state.get("workflow_status") or "-")),
            ("current_stage", str(state.get("current_stage_id") or "-")),
            ("stage_status", str(state.get("stage_status") or "-")),
            (
                "allowed_next_stages",
                ", ".join(str(item) for item in state.get("allowed_next_stages", ()))
                or "(none)",
            ),
            (
                "pending_approvals",
                ", ".join(str(item) for item in state.get("pending_approvals", ()))
                or "(none)",
            ),
            ("blocked_by", ", ".join(blocked_by) or "(none)"),
            (
                "next_artifact",
                str(next_stage.get("stage_id"))
                if isinstance(next_stage, dict)
                else "(none)",
            ),
            (
                "next_artifact_status",
                str(next_stage.get("summary_status"))
                if isinstance(next_stage, dict)
                else "(none)",
            ),
        ]
    )
    stage_lines = [
        (
            f"- {record.record_id}  stage={record.stage_id}  status={record.status}"
            + (
                f"  run={record.run_id}"
                if record.run_id is not None
                else ""
            )
        ).strip()
        for record in sorted(
            stage_records,
            key=lambda record: (
                record.updated_at or "",
                record.created_at or "",
                record.record_id,
            ),
        )[-5:]
    ]
    stage_body = "\n".join(stage_lines) if stage_lines else "(none)"
    return (
        ItemDossierSection(
            kind="workflow",
            title="Related Workflow Status",
            ref=str(state.get("item_ref") or ""),
            body=workflow_body,
            metadata={"state": state, "workflow": workflow},
        ),
        ItemDossierSection(
            kind="stage_records",
            title="Latest Stage Records",
            ref=str(state.get("item_ref") or ""),
            body=stage_body,
            metadata={"count": len(stage_records)},
        ),
    )


def _runs_section(paths, item: WorkItem, *, stage_records: list) -> ItemDossierSection:
    run_records = load_run_records(paths, limit=None)
    run_by_id = {record.run_id: record for record in run_records}
    ordered_run_ids: list[str] = []
    for run_id in item.linked_runs:
        if run_id not in ordered_run_ids:
            ordered_run_ids.append(run_id)
    for record in stage_records:
        if record.run_id and record.run_id not in ordered_run_ids:
            ordered_run_ids.append(record.run_id)
    for record in run_records:
        if record.project_item_ref == item.id and record.run_id not in ordered_run_ids:
            ordered_run_ids.append(record.run_id)

    lines: list[str] = []
    serialized_runs: list[dict[str, object]] = []
    for run_id in ordered_run_ids:
        run = run_by_id.get(run_id)
        if run is None:
            lines.append(f"- {run_id}  (missing)")
            serialized_runs.append({"run_id": run_id, "missing": True})
            continue
        lines.append(
            f"- {run.run_id}  {run.status}  stage={run.stage or '-'}  "
            f"started={run.started_at}"
        )
        serialized_runs.append(run.to_dict())
    body = "\n".join(lines) if lines else "(none)"
    return ItemDossierSection(
        kind="runs",
        title="Related Runs",
        ref=item.id,
        body=body,
        metadata={"runs": serialized_runs},
    )


def _validation_section(
    paths,
    item: WorkItem,
    *,
    stage_records: list,
) -> ItemDossierSection:
    validation_records = load_validation_records(paths)
    stage_validation_refs = {
        ref
        for record in stage_records
        for ref in record.validation_record_refs
    }
    selected: list[dict[str, object]] = []
    selected_ids: set[str] = set()
    for record in validation_records:
        record_id = str(record.get("id", ""))
        project_item_ref = str(record.get("project_item_ref", ""))
        if project_item_ref != item.id and record_id not in stage_validation_refs:
            continue
        if record_id in selected_ids:
            continue
        selected.append(record)
        selected_ids.add(record_id)
    for validation_id in sorted(stage_validation_refs):
        if validation_id in selected_ids:
            continue
        selected.append({"id": validation_id, "missing": True})

    lines = [
        (
            f"- {record.get('id')}  {record.get('kind', '-')}"
            f"  {record.get('status', '-')}"
            f"  memory={record.get('memory_ref', '-')}"
        )
        if not record.get("missing")
        else f"- {record.get('id')}  (missing)"
        for record in selected
    ]
    body = "\n".join(lines) if lines else "(none)"
    return ItemDossierSection(
        kind="validation",
        title="Related Validation Records",
        ref=item.id,
        body=body,
        metadata={"records": selected},
    )


def _referencing_contexts_section(paths, item: WorkItem) -> ItemDossierSection:
    contexts = load_contexts(paths)
    references = [
        context
        for context in contexts
        if item.id in context.item_refs or item.slug in context.item_refs
    ]
    lines = [
        (
            f"- {context.name} ({context.id})  "
            f"memories={len(context.memory_refs)} files={len(context.file_refs)} "
            f"items={len(context.item_refs)}"
        )
        for context in references
    ]
    body = "\n".join(lines) if lines else "(none)"
    return ItemDossierSection(
        kind="contexts",
        title="Contexts Referencing This Item",
        ref=item.id,
        body=body,
        metadata={"contexts": [context.to_dict() for context in references]},
    )


def _list_section(kind: str, title: str, values: tuple[str, ...]) -> ItemDossierSection:
    cleaned = [value.strip() for value in values if value.strip()]
    body = "\n".join(f"- {value}" for value in cleaned) if cleaned else "(none)"
    return ItemDossierSection(
        kind=kind,
        title=title,
        ref=None,
        body=body,
        metadata={"count": len(cleaned)},
    )


def _kv_block(rows: list[tuple[str, object]]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in rows if value is not None)


def _approve_item(paths, item: WorkItem) -> WorkItem:
    if item.status == "closed":
        raise LaunchError(f"Project work item {item.id} is closed.")
    if not _has_planning_evidence(paths, item):
        raise LaunchError(
            f"Project work item {item.id} cannot be approved without plan content, "
            "acceptance criteria, or a validation checklist."
        )
    return replace(
        item,
        status="approved",
        stage="approval",
        approved_at=utc_now_iso(),
        workflow_id=item.workflow_id,
        workflow_status="ready",
        stage_status="ready",
    )


def _reopen_item(paths, item: WorkItem) -> WorkItem:
    if item.status != "closed":
        raise LaunchError(f"Project work item {item.id} is not closed.")
    if _has_planning_evidence(paths, item):
        status = "planned"
        stage = "approval"
    else:
        status = "draft"
        stage = "intake"
    return replace(
        item,
        status=status,
        stage=stage,
        closed_at=None,
        workflow_status="draft" if status == "draft" else "waiting_approval",
        stage_status="not_started",
    )


def _close_item(item: WorkItem) -> WorkItem:
    if item.status == "closed":
        raise LaunchError(f"Project work item {item.id} is already closed.")
    return replace(
        item,
        status="closed",
        stage="closure",
        closed_at=utc_now_iso(),
        workflow_status="closed",
        stage_status="succeeded",
    )


def _memory_refs_for_item(item: WorkItem) -> dict[str, str | None]:
    return {
        role: getattr(item, field_name)
        for role, field_name in _ITEM_MEMORY_ROLE_FIELDS.items()
    }


def _canonical_item_memory_role(role: str) -> str:
    normalized_role = role.strip().lower()
    return _ITEM_MEMORY_ROLE_ALIASES.get(normalized_role, normalized_role)


def _memory_field_for_role(role: str) -> str:
    field_name = _ITEM_MEMORY_ROLE_FIELDS.get(_canonical_item_memory_role(role))
    if field_name is None:
        raise LaunchError(
            "Invalid item memory role. Use one of: "
            + ", ".join(sorted({*_ITEM_MEMORY_ROLE_FIELDS, *_ITEM_MEMORY_ROLE_ALIASES}))
        )
    return field_name


def _drop_memory_refs(item: WorkItem, memory_id: str) -> WorkItem:
    updates = {
        field_name: None
        for field_name in _ITEM_MEMORY_ROLE_FIELDS.values()
        if getattr(item, field_name) == memory_id
    }
    linked_memories = tuple(ref for ref in item.linked_memories if ref != memory_id)
    return replace(item, linked_memories=linked_memories, **updates)


def _create_item_memory(
    paths: ProjectPaths, item: WorkItem, *, role: str, body: str
) -> Memory:
    memory = create_memory(paths, name=_item_memory_name(item, role), body=body)
    linked_memories = item.linked_memories
    if memory.id not in linked_memories:
        linked_memories = linked_memories + (memory.id,)
    field_name = _memory_field_for_role(role)
    save_target_ref = item.save_target_ref
    if role == "implementation" and save_target_ref is None:
        save_target_ref = memory.id
    updated_item = replace(
        item,
        linked_memories=linked_memories,
        save_target_ref=save_target_ref,
        **{field_name: memory.id},
    )
    update_work_item(paths, item.id, updated_item)
    return memory


def _item_memory_name(item: WorkItem, role: str) -> str:
    role_label = {
        "analysis": "analysis",
        "current": "current-state",
        "plan": "plan",
        "implementation": "implementation",
        "validation": "validation",
        "save_target": "save-target",
    }[role]
    return f"{item.slug} {role_label}"


def _memory_ref_has_content(paths, ref: str | None) -> bool:
    if not ref:
        return False
    try:
        memory = resolve_memory(paths, ref)
    except LaunchError:
        return False
    return bool(read_memory_body(paths, memory).strip())


def _has_planning_evidence(paths, item: WorkItem) -> bool:
    if _memory_ref_has_content(paths, item.plan_memory_ref):
        return True
    if any(entry.strip() for entry in item.acceptance_criteria):
        return True
    if any(entry.strip() for entry in item.validation_checklist):
        return True
    return False


def _normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise LaunchError(f"Item {field_name} must not be empty.")
    return normalized


def _normalize_text_values(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        candidate = value.strip()
        if not candidate:
            raise LaunchError(f"Item {field_name} must not be empty.")
        if candidate in normalized:
            continue
        normalized.append(candidate)
    return tuple(normalized)


def _apply_sequence_patch(
    existing: tuple[str, ...],
    add_values: tuple[str, ...],
    remove_values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    current = list(existing)
    for value in remove_values:
        if value not in current:
            raise LaunchError(f"Cannot remove unknown item {field_name}: {value}")
        current.remove(value)
    for value in add_values:
        if value in current:
            continue
        current.append(value)
    return tuple(current)


def _title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().title() or "Project Work Item"


def _item_summary_payload(state, item: WorkItem) -> dict[str, object]:
    workflow_payload = item_workflow_state_payload(state, item)
    stage_records = item_stage_records_for_paths(
        state.paths,
        item.id,
        workflow_id=item.workflow_id or default_workflow_id_for_paths(state.paths),
    )
    stage_detail = _resolve_summary_stage(workflow_payload, stage_id=None)
    next_action = _next_action_summary(item, workflow_payload, stage_detail)
    recent_runs = [
        _run_summary_payload(record, stage_records=stage_records)
        for record in _related_run_records(
            state.paths,
            item,
            stage_records=stage_records,
        )[:5]
    ]
    validation_records = [
        _validation_summary_payload(record)
        for record in _related_validation_records(
            state.paths,
            item,
            stage_records=stage_records,
        )[:5]
    ]
    return {
        "item": {
            "id": item.id,
            "slug": item.slug,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "workflow_id": (
                item.workflow_id or default_workflow_id_for_paths(state.paths)
            ),
            "stage": (
                str(stage_detail["stage_id"]) if stage_detail is not None else None
            ),
            "repo_refs": list(item.repo_refs),
            "target_repo_ref": item.target_repo_ref,
            "save_target_ref": item.save_target_ref,
        },
        "next_action": next_action,
        "memories": {
            role: _memory_summary_payload(state.paths, getattr(item, field_name))
            for role, field_name in _ITEM_MEMORY_ROLE_FIELDS.items()
            if role != "save_target"
        },
        "acceptance_criteria": list(item.acceptance_criteria),
        "validation_checks": list(item.validation_checklist),
        "context_refs": _referencing_context_refs(state.paths, item),
        "recent_runs": recent_runs,
        "validation_records": validation_records,
    }


def _memory_summary_payload(paths, memory_ref: str | None) -> dict[str, object] | None:
    if memory_ref is None:
        return None
    try:
        memory = refresh_memory(paths, memory_ref)
    except LaunchError:
        return {"ref": memory_ref, "excerpt": None, "missing": True}
    body = read_memory_body(paths, memory).strip()
    excerpt = memory.summary or summarize_text(body) or None
    return {"ref": memory.id, "excerpt": excerpt}


def _resolve_summary_stage(
    workflow_payload: dict[str, object],
    *,
    stage_id: str | None,
) -> dict[str, object] | None:
    stages = workflow_payload.get("stages")
    if not isinstance(stages, list):
        return None
    if stage_id is not None:
        stage_detail = next(
            (
                stage
                for stage in stages
                if isinstance(stage, dict) and stage.get("stage_id") == stage_id
            ),
            None,
        )
        if stage_detail is None:
            raise LaunchError(f"Unknown workflow stage: {stage_id}")
        if bool(stage_detail.get("complete")):
            raise LaunchError(f"Workflow stage {stage_id} is already complete.")
        return stage_detail
    for stage in stages:
        if not isinstance(stage, dict) or bool(stage.get("complete")):
            continue
        stage_status = str(stage.get("stage_status") or "not_started")
        if stage_status in _ACTIONABLE_STAGE_STATUSES:
            return stage
    return next(
        (
            stage
            for stage in stages
            if isinstance(stage, dict) and not bool(stage.get("complete"))
        ),
        None,
    )


def _next_action_summary(
    item: WorkItem,
    workflow_payload: dict[str, object],
    stage_detail: dict[str, object] | None,
) -> dict[str, object]:
    state = workflow_payload.get("state")
    state = state if isinstance(state, dict) else {}
    if stage_detail is not None:
        stage_id = str(stage_detail.get("stage_id") or "")
        label = str(stage_detail.get("label") or stage_id)
        stage_status = str(stage_detail.get("stage_status") or "not_started")
        blocked_by = _stage_blocked_by(stage_detail)
        if stage_status in _ACTIONABLE_STAGE_STATUSES:
            verb = (
                "Continue"
                if stage_status in {"running", "failed", "needs_review"}
                else "Start"
            )
            return {
                "kind": "work_stage",
                "stage": stage_id,
                "label": f"{verb} {label.lower()}",
                "status": stage_status,
                "blocked_by": blocked_by,
            }
        if "approval:item" in blocked_by:
            return {
                "kind": "approval",
                "stage": stage_id,
                "label": f"Approve {label.lower()}",
                "status": stage_status,
                "blocked_by": blocked_by,
            }
        if blocked_by:
            return {
                "kind": "blocked_stage",
                "stage": stage_id,
                "label": f"Unblock {label.lower()}",
                "status": stage_status,
                "blocked_by": blocked_by,
            }
    legacy = next_action_payload(item)
    return {
        "kind": str(legacy["kind"]),
        "stage": state.get("current_stage_id"),
        "label": str(legacy["action"]).replace("_", " ").title(),
        "status": state.get("stage_status"),
        "blocked_by": list(state.get("blocking_reasons", ()))
        if isinstance(state.get("blocking_reasons"), list)
        else [],
    }


def _related_run_records(paths, item: WorkItem, *, stage_records: list) -> list[object]:
    all_runs = load_run_records(paths, limit=None)
    selected = [
        record
        for record in all_runs
        if record.project_item_ref == item.id
        or record.run_id in item.linked_runs
        or any(stage_record.run_id == record.run_id for stage_record in stage_records)
    ]
    return sorted(
        selected,
        key=lambda record: (
            record.finished_at,
            record.started_at,
            record.run_id,
        ),
        reverse=True,
    )


def _run_summary_payload(record, *, stage_records: list) -> dict[str, object]:
    stage = _stage_id_from_run(record, stage_records=stage_records)
    return {
        "id": record.run_id,
        "stage": stage,
        "status": record.status,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "summary": record.output_summary or record.prompt_summary,
    }


def _stage_id_from_run(record, *, stage_records: list) -> str | None:
    stage_record = next(
        (
            current
            for current in sorted(
                stage_records,
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
    mapping = {
        "analysis": "analysis",
        "state": "state",
        "plan": "plan",
        "implementation": "implement",
        "validation": "validate",
    }
    return mapping.get(record.stage) if record.stage is not None else None


def _related_validation_records(
    paths,
    item: WorkItem,
    *,
    stage_records: list,
) -> list[dict[str, object]]:
    stage_validation_refs = {
        ref for record in stage_records for ref in record.validation_record_refs
    }
    records = [
        record
        for record in load_validation_records(paths)
        if str(record.get("project_item_ref")) == item.id
        or str(record.get("id")) in stage_validation_refs
    ]
    return sorted(
        records,
        key=lambda record: (
            str(record.get("created_at") or ""),
            str(record.get("id") or ""),
        ),
        reverse=True,
    )


def _validation_summary_payload(record: dict[str, object]) -> dict[str, object]:
    summary = record.get("notes") or record.get("verdict") or record.get("status")
    return {
        "id": str(record.get("id") or ""),
        "status": str(record.get("status") or "unknown"),
        "kind": str(record.get("kind") or "unknown"),
        "run_id": record.get("run_id"),
        "memory_ref": record.get("memory_ref"),
        "summary": str(summary) if summary is not None else None,
    }


def _memory_role_for_stage_detail(stage_detail: dict[str, object]) -> str | None:
    stage_id = stage_detail.get("stage_id")
    if isinstance(stage_id, str) and stage_id in _STAGE_ROLE_BY_STAGE_ID:
        return _STAGE_ROLE_BY_STAGE_ID[stage_id]
    kind = stage_detail.get("kind")
    if isinstance(kind, str):
        return _STAGE_ROLE_BY_KIND.get(kind)
    return None


def _save_target_ref_for_stage(
    item: WorkItem,
    stage_detail: dict[str, object],
) -> str | None:
    suggested_memory_role = _memory_role_for_stage_detail(stage_detail)
    if suggested_memory_role is not None:
        field_name = _memory_field_for_role(suggested_memory_role)
        stage_memory_ref = getattr(item, field_name)
        if isinstance(stage_memory_ref, str):
            return stage_memory_ref
    if str(stage_detail.get("save_target_rule") or "") == "validation_record":
        return None
    return item.save_target_ref


def _build_work_prompt_text(
    item: WorkItem,
    *,
    stage_detail: dict[str, object],
    target_repo_ref: str | None,
    save_target_ref: str | None,
    suggested_memory_role: str | None,
    blocked_by: list[str],
) -> str:
    label = str(stage_detail.get("label") or stage_detail.get("stage_id") or "work")
    stage_id = str(stage_detail.get("stage_id") or "")
    stage_status = str(stage_detail.get("stage_status") or "not_started")
    lines = [
        f"Work on Taskledger item {item.slug} ({item.id}).",
        (
            f"Continue the {label.lower()} stage ({stage_id})."
            if stage_status in {"running", "failed", "needs_review"}
            else f"Focus on the {label.lower()} stage ({stage_id})."
        ),
        item.description.strip(),
    ]
    if target_repo_ref:
        lines.append(f"Use repo {target_repo_ref}.")
    if save_target_ref:
        lines.append(f"Save important notes to {save_target_ref}.")
    elif suggested_memory_role:
        lines.append(
            "Save important notes to the "
            f"{suggested_memory_role} memory when appropriate."
        )
    if blocked_by:
        lines.append("Current blockers: " + ", ".join(blocked_by) + ".")
    return "\n\n".join(line for line in lines if line)


def _referencing_context_refs(paths, item: WorkItem) -> list[str]:
    return [
        context.id
        for context in load_contexts(paths)
        if item.id in context.item_refs or item.slug in context.item_refs
    ]


def _stage_blocked_by(stage_detail: dict[str, object]) -> list[str]:
    blocked = stage_detail.get("blocked_by")
    if not isinstance(blocked, list):
        return []
    return [str(reason) for reason in blocked]


def _ensure_stage_can_complete(stage_detail: dict[str, object]) -> None:
    if bool(stage_detail.get("complete")):
        raise LaunchError(
            f"Workflow stage {stage_detail['stage_id']} is already complete."
        )
    stage_status = str(stage_detail.get("stage_status") or "not_started")
    blocked_by = _stage_blocked_by(stage_detail)
    if stage_status in {"running", "failed", "needs_review", "ready"}:
        return
    reason = ", ".join(blocked_by) if blocked_by else stage_status
    raise LaunchError(
        f"Workflow stage {stage_detail['stage_id']} cannot be completed: {reason}"
    )


def _resolved_run_payloads(
    workspace_root: Path,
    run_refs: tuple[str, ...],
) -> list[dict[str, object]]:
    paths = load_project_state(workspace_root).paths
    available_runs = {
        record.run_id: record
        for record in load_run_records(paths, limit=None)
    }
    resolved: list[dict[str, object]] = []
    for run_ref in run_refs:
        run = available_runs.get(run_ref)
        if run is None:
            raise LaunchError(f"Unknown project run: {run_ref}")
        resolved.append({"id": run.run_id, "stage": run.stage, "status": run.status})
    return resolved


def _resolved_validation_refs(
    workspace_root: Path,
    validation_refs: tuple[str, ...],
) -> tuple[str, ...]:
    if not validation_refs:
        return ()
    record_ids = {
        str(record.get("id"))
        for record in load_validation_records(load_project_state(workspace_root).paths)
    }
    normalized: list[str] = []
    for ref in validation_refs:
        if ref not in record_ids:
            raise LaunchError(f"Unknown validation record: {ref}")
        if ref not in normalized:
            normalized.append(ref)
    return tuple(normalized)


def _attach_run_refs_to_item(
    paths,
    item: WorkItem,
    run_refs: tuple[str, ...],
) -> WorkItem:
    if not run_refs:
        return item
    linked_runs = list(item.linked_runs)
    for run_ref in run_refs:
        if run_ref not in linked_runs:
            linked_runs.append(run_ref)
    updated = replace(item, linked_runs=tuple(linked_runs))
    return update_work_item(paths, item.id, updated)


def _workflow_state_summary(summary_payload: dict[str, object]) -> dict[str, object]:
    item = summary_payload.get("item")
    next_action = summary_payload.get("next_action")
    assert isinstance(item, dict)
    assert isinstance(next_action, dict)
    return {
        "current_stage": item.get("stage"),
        "status": item.get("status"),
        "next_action": next_action.get("kind"),
    }
