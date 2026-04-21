from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.api.types import Memory, WorkItem
from taskledger.errors import LaunchError
from taskledger.models import utc_now_iso
from taskledger.storage import (
    create_memory,
    create_work_item,
    delete_memory,
    load_project_state,
    load_work_items,
    read_memory_body,
    rename_memory,
    resolve_memory,
    resolve_work_item,
    update_memory_body,
    update_memory_tags,
    update_work_item,
    write_memory_body,
)
from taskledger.workflow import default_workflow_id_for_paths

_ITEM_MEMORY_ROLE_FIELDS = {
    "analysis": "analysis_memory_ref",
    "state": "state_memory_ref",
    "plan": "plan_memory_ref",
    "implementation": "implementation_memory_ref",
    "validation": "validation_memory_ref",
    "save_target": "save_target_ref",
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
    analysis_memory = create_memory(paths, name=f"{normalized_slug} analysis")
    state_memory = create_memory(paths, name=f"{normalized_slug} current-state")
    plan_memory = create_memory(paths, name=f"{normalized_slug} plan")
    implementation_memory = create_memory(
        paths,
        name=f"{normalized_slug} implementation",
    )
    validation_memory = create_memory(paths, name=f"{normalized_slug} validation")
    return create_work_item(
        paths,
        slug=normalized_slug,
        title=title or _title_from_slug(normalized_slug),
        description=description,
        source_path=source_path,
        repo_refs=repo_refs,
        target_repo_ref=target_repo_ref,
        analysis_memory_ref=analysis_memory.id,
        state_memory_ref=state_memory.id,
        plan_memory_ref=plan_memory.id,
        implementation_memory_ref=implementation_memory.id,
        validation_memory_ref=validation_memory.id,
        linked_memories=(
            analysis_memory.id,
            state_memory.id,
            plan_memory.id,
            implementation_memory.id,
            validation_memory.id,
        ),
        save_target_ref=implementation_memory.id,
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
    field_name = _memory_field_for_role(role)
    memory_ref = getattr(item, field_name)
    if not memory_ref:
        raise LaunchError(f"Project work item {item.id} has no {role} memory.")
    try:
        return resolve_memory(paths, memory_ref)
    except LaunchError as exc:
        raise LaunchError(
            f"Project work item {item.id} has invalid {role} memory ref: {memory_ref}"
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
    memory = resolve_item_memory(workspace_root, item_ref, role)
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


def _memory_field_for_role(role: str) -> str:
    field_name = _ITEM_MEMORY_ROLE_FIELDS.get(role.strip().lower())
    if field_name is None:
        raise LaunchError(
            "Invalid item memory role. Use one of: "
            + ", ".join(sorted(_ITEM_MEMORY_ROLE_FIELDS))
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
