from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.api.types import WorkItem
from taskledger.errors import LaunchError
from taskledger.models import utc_now_iso
from taskledger.storage import (
    create_memory,
    create_work_item,
    load_project_state,
    load_work_items,
    resolve_work_item,
    update_work_item,
)


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
    )


def list_items(workspace_root: Path) -> list[WorkItem]:
    return load_work_items(load_project_state(workspace_root).paths)


def show_item(workspace_root: Path, ref: str) -> WorkItem:
    return resolve_work_item(load_project_state(workspace_root).paths, ref)


def approve_item(workspace_root: Path, ref: str) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)
    return update_work_item(paths, ref, _approve_item(item))


def reopen_item(workspace_root: Path, ref: str) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)
    return update_work_item(paths, ref, _reopen_item(item))


def close_item(workspace_root: Path, ref: str) -> WorkItem:
    paths = load_project_state(workspace_root).paths
    item = resolve_work_item(paths, ref)
    return update_work_item(paths, ref, _close_item(item))


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


def _approve_item(item: WorkItem) -> WorkItem:
    if item.status == "closed":
        raise LaunchError(f"Project work item {item.id} is closed.")
    return replace(
        item,
        status="approved",
        stage="execution",
        approved_at=utc_now_iso(),
    )


def _reopen_item(item: WorkItem) -> WorkItem:
    if item.status != "closed":
        raise LaunchError(f"Project work item {item.id} is not closed.")
    if item.plan_memory_ref or item.acceptance_criteria or item.validation_checklist:
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
    )


def _close_item(item: WorkItem) -> WorkItem:
    if item.status == "closed":
        raise LaunchError(f"Project work item {item.id} is already closed.")
    return replace(
        item,
        status="closed",
        stage="closure",
        closed_at=utc_now_iso(),
    )


def _title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().title() or "Project Work Item"
