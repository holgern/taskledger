from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.ids import slugify_project_ref as _slugify
from taskledger.models import (
    ProjectPaths,
    ProjectWorkItem,
    WorkflowStageStatus,
    WorkflowStatus,
    WorkItemStage,
    WorkItemStatus,
    utc_now_iso,
)
from taskledger.storage.common import load_json_array as _load_json_array
from taskledger.storage.common import write_json as _write_json

_WORK_ITEM_STATUSES = {
    "draft",
    "planned",
    "approved",
    "in_progress",
    "implemented",
    "validated",
    "closed",
    "rejected",
}
_WORK_ITEM_STAGES = {
    "intake",
    "planning",
    "approval",
    "execution",
    "validation",
    "closure",
}


def load_work_items(paths: ProjectPaths) -> list[ProjectWorkItem]:
    return [
        ProjectWorkItem.from_dict(item)
        for item in _load_json_array(paths.item_index_path, "project work item index")
    ]


def save_work_items(paths: ProjectPaths, items: list[ProjectWorkItem]) -> None:
    _write_json(paths.item_index_path, [item.to_dict() for item in items])


def save_work_item(paths: ProjectPaths, item: ProjectWorkItem) -> ProjectWorkItem:
    items = load_work_items(paths)
    _replace_work_item(items, replace(item, updated_at=utc_now_iso()))
    save_work_items(paths, items)
    return items[_work_item_index(items, item.id)]


def create_work_item(
    paths: ProjectPaths,
    *,
    slug: str,
    title: str,
    description: str,
    source_path: Path | str | None = None,
    repo_refs: tuple[str, ...] = (),
    target_repo_ref: str | None = None,
    status: str = "draft",
    stage: str = "intake",
    discovered_file_refs: tuple[str, ...] = (),
    acceptance_criteria: tuple[str, ...] = (),
    validation_checklist: tuple[str, ...] = (),
    notes: str | None = None,
    estimate: str | None = None,
    owner: str | None = None,
    labels: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
    analysis_memory_ref: str | None = None,
    state_memory_ref: str | None = None,
    plan_memory_ref: str | None = None,
    implementation_memory_ref: str | None = None,
    validation_memory_ref: str | None = None,
    linked_memories: tuple[str, ...] = (),
    linked_runs: tuple[str, ...] = (),
    linked_loop_tasks: tuple[str, ...] = (),
    save_target_ref: str | None = None,
    workflow_id: str | None = None,
    current_stage_id: str | None = None,
    workflow_status: str = "draft",
    stage_status: str | None = "not_started",
) -> ProjectWorkItem:
    if status not in _WORK_ITEM_STATUSES:
        raise LaunchError(f"Unsupported work item status: {status}")
    if stage not in _WORK_ITEM_STAGES:
        raise LaunchError(f"Unsupported work item stage: {stage}")
    items = load_work_items(paths)
    normalized_slug = _slugify(slug, empty="item")
    _ensure_unique_slug(items, normalized_slug)
    now = utc_now_iso()
    item = ProjectWorkItem(
        id=_next_id("item", [entry.id for entry in items]),
        slug=normalized_slug,
        title=title,
        description=description,
        source_path=str(source_path) if source_path is not None else None,
        repo_refs=repo_refs,
        target_repo_ref=target_repo_ref,
        status=cast(WorkItemStatus, status),
        stage=cast(WorkItemStage, stage),
        created_at=now,
        updated_at=now,
        discovered_file_refs=discovered_file_refs,
        acceptance_criteria=acceptance_criteria,
        validation_checklist=validation_checklist,
        notes=notes,
        estimate=estimate,
        owner=owner,
        labels=labels,
        depends_on=depends_on,
        analysis_memory_ref=analysis_memory_ref,
        state_memory_ref=state_memory_ref,
        plan_memory_ref=plan_memory_ref,
        implementation_memory_ref=implementation_memory_ref,
        validation_memory_ref=validation_memory_ref,
        linked_memories=linked_memories,
        linked_runs=linked_runs,
        linked_loop_tasks=linked_loop_tasks,
        save_target_ref=save_target_ref,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
        workflow_status=cast(WorkflowStatus, workflow_status),
        stage_status=cast(WorkflowStageStatus | None, stage_status),
    )
    items.append(item)
    save_work_items(paths, items)
    return item


def resolve_work_item(paths: ProjectPaths, ref: str) -> ProjectWorkItem:
    items = load_work_items(paths)
    normalized_ref = _slugify(ref, empty="item")
    candidates = [
        item
        for item in items
        if item.id == ref
        or item.slug == ref
        or item.slug == normalized_ref
        or item.title == ref
        or _slugify(item.title, empty="item") == normalized_ref
    ]
    if not candidates:
        raise LaunchError(f"Unknown project work item: {ref}")
    if len(candidates) > 1:
        raise LaunchError(f"Ambiguous project work item ref: {ref}")
    return candidates[0]


def update_work_item(
    paths: ProjectPaths,
    ref: str,
    item: ProjectWorkItem,
) -> ProjectWorkItem:
    existing = resolve_work_item(paths, ref)
    if item.id != existing.id:
        raise LaunchError("Project work item id cannot be changed.")
    items = load_work_items(paths)
    if item.slug != existing.slug:
        _ensure_unique_slug(items, item.slug, ignore_id=item.id)
    updated = replace(item, updated_at=utc_now_iso())
    _replace_work_item(items, updated)
    save_work_items(paths, items)
    return updated


def _replace_work_item(items: list[ProjectWorkItem], updated: ProjectWorkItem) -> None:
    index = _work_item_index(items, updated.id)
    items[index] = updated


def _work_item_index(items: list[ProjectWorkItem], item_id: str) -> int:
    for index, item in enumerate(items):
        if item.id == item_id:
            return index
    raise LaunchError(f"Unknown project work item: {item_id}")


def _ensure_unique_slug(
    items: list[ProjectWorkItem],
    slug: str,
    *,
    ignore_id: str | None = None,
) -> None:
    for item in items:
        if ignore_id is not None and item.id == ignore_id:
            continue
        if item.slug == slug:
            raise LaunchError(f"Project work item already exists with slug: {slug}")
