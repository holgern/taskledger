from __future__ import annotations

import re
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
from taskledger.storage.frontmatter import (
    MARKDOWN_FILE_VERSION,
)
from taskledger.storage.frontmatter import (
    iter_markdown_files as _iter_markdown_files,
)
from taskledger.storage.frontmatter import (
    read_markdown_front_matter as _read_markdown_front_matter,
)
from taskledger.storage.frontmatter import (
    write_markdown_front_matter as _write_markdown_front_matter,
)

_NUMERIC_SUFFIX_PATTERN = re.compile(r".*-(\d+)$")
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
_REQUIRED_ITEM_KEYS = (
    "file_version",
    "id",
    "slug",
    "title",
    "status",
    "stage",
    "created_at",
    "updated_at",
)


def load_work_items(paths: ProjectPaths) -> list[ProjectWorkItem]:
    items: list[ProjectWorkItem] = []
    for item_file in _iter_markdown_files(paths.items_dir):
        metadata, body = _read_markdown_front_matter(item_file)
        _validate_required_keys(metadata, item_file)
        _validate_file_version(metadata, item_file)
        item_id = _string_metadata_value(metadata, "id", path=item_file)
        if item_file.stem != item_id:
            raise LaunchError(
                "Invalid work item document "
                f"{item_file}: filename stem {item_file.stem!r} does not match "
                f"front matter id {item_id!r}."
            )
        payload = dict(metadata)
        payload["description"] = body
        try:
            items.append(ProjectWorkItem.from_dict(payload))
        except (TypeError, ValueError) as exc:
            raise LaunchError(
                f"Invalid work item front matter {item_file}: {exc}"
            ) from exc
    items.sort(key=lambda item: _id_sort_key(item.id))
    return items


def save_work_items(paths: ProjectPaths, items: list[ProjectWorkItem]) -> None:
    keep_ids: set[str] = set()
    for item in sorted(items, key=lambda entry: _id_sort_key(entry.id)):
        _write_work_item_document(paths, item)
        keep_ids.add(item.id)
    for stale_path in _iter_markdown_files(paths.items_dir):
        if stale_path.stem in keep_ids:
            continue
        try:
            stale_path.unlink()
        except OSError as exc:
            raise LaunchError(
                f"Failed to delete work item file {stale_path}: {exc}"
            ) from exc


def save_work_item(paths: ProjectPaths, item: ProjectWorkItem) -> ProjectWorkItem:
    items = load_work_items(paths)
    existing = _resolve_item_by_id(items, item.id)
    if item.slug != existing.slug:
        _ensure_unique_slug(items, item.slug, ignore_id=item.id)
    updated = replace(item, updated_at=utc_now_iso())
    _write_work_item_document(paths, updated)
    return updated


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
        id=_next_id("it", [entry.id for entry in items]),
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
    _write_work_item_document(paths, item)
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
    _write_work_item_document(paths, updated)
    return updated


def _resolve_item_by_id(items: list[ProjectWorkItem], item_id: str) -> ProjectWorkItem:
    for item in items:
        if item.id == item_id:
            return item
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


def _id_sort_key(value: str) -> tuple[int, int, str]:
    match = _NUMERIC_SUFFIX_PATTERN.match(value)
    if match is None:
        return (1, 0, value)
    return (0, int(match.group(1)), value)


def _write_work_item_document(paths: ProjectPaths, item: ProjectWorkItem) -> None:
    metadata = item.to_dict()
    metadata.pop("description", None)
    metadata["file_version"] = MARKDOWN_FILE_VERSION
    _write_markdown_front_matter(
        paths.items_dir / f"{item.id}.md",
        metadata,
        item.description,
    )


def _string_metadata_value(metadata: dict[str, object], key: str, *, path: Path) -> str:
    value = metadata.get(key)
    if isinstance(value, str):
        return value
    raise LaunchError(
        f"Invalid work item front matter {path}: key {key!r} must be a string."
    )


def _validate_required_keys(metadata: dict[str, object], path: Path) -> None:
    missing = [key for key in _REQUIRED_ITEM_KEYS if key not in metadata]
    if not missing:
        return
    missing_text = ", ".join(missing)
    raise LaunchError(
        f"Invalid work item front matter {path}: missing required keys: {missing_text}."
    )


def _validate_file_version(metadata: dict[str, object], path: Path) -> None:
    value = metadata.get("file_version")
    if not isinstance(value, str):
        raise LaunchError(
            "Invalid work item front matter "
            f"{path}: key 'file_version' must be a string."
        )
    if value != MARKDOWN_FILE_VERSION:
        raise LaunchError(
            f"Unsupported work item file_version {value!r} in {path}; "
            f"expected {MARKDOWN_FILE_VERSION!r}."
        )
