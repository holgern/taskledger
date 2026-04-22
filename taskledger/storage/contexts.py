from __future__ import annotations

from dataclasses import replace

from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.ids import slugify_project_ref as _slugify
from taskledger.models import ProjectContextEntry, ProjectPaths, utc_now_iso
from taskledger.storage.common import load_json_array as _load_json_array
from taskledger.storage.common import (
    relative_to_project as _relative_to_project,
)
from taskledger.storage.common import write_json as _write_json


def load_contexts(paths: ProjectPaths) -> list[ProjectContextEntry]:
    return [
        ProjectContextEntry.from_dict(item)
        for item in _load_json_array(paths.context_index_path, "context index")
    ]


def save_contexts(paths: ProjectPaths, entries: list[ProjectContextEntry]) -> None:
    _write_json(paths.context_index_path, [item.to_dict() for item in entries])
    for entry in entries:
        context_path = paths.project_dir / entry.path
        _write_json(context_path, entry.to_dict())


def save_context(
    paths: ProjectPaths,
    *,
    name: str,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    directory_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
) -> ProjectContextEntry:
    entries = load_contexts(paths)
    slug = _slugify(name)
    existing = next((item for item in entries if item.slug == slug), None)
    if existing is None:
        _ensure_unique_context_identity(entries, name=name, slug=slug)
    now = utc_now_iso()
    context_id = (
        existing.id
        if existing is not None
        else _next_id("ctx", [item.id for item in entries])
    )
    entry = ProjectContextEntry(
        id=context_id,
        name=name,
        slug=slug,
        path=_relative_to_project(paths, paths.contexts_dir / f"{slug}.json"),
        memory_refs=memory_refs,
        file_refs=file_refs,
        directory_refs=directory_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
        summary=_context_summary(
            memory_refs=memory_refs,
            file_refs=file_refs,
            directory_refs=directory_refs,
            item_refs=item_refs,
            inline_texts=inline_texts,
            loop_latest_refs=loop_latest_refs,
        ),
        created_at=existing.created_at if existing is not None else now,
        updated_at=now,
    )
    remaining = [item for item in entries if item.slug != slug]
    remaining.append(entry)
    remaining.sort(key=lambda item: item.slug)
    save_contexts(paths, remaining)
    return entry


def save_context_entry(
    paths: ProjectPaths, entry: ProjectContextEntry
) -> ProjectContextEntry:
    entries = load_contexts(paths)
    _replace_context(entries, entry)
    save_contexts(paths, entries)
    return entry


def resolve_context(paths: ProjectPaths, ref: str) -> ProjectContextEntry:
    entries = load_contexts(paths)
    candidates = [
        item
        for item in entries
        if item.id == ref
        or item.slug == ref
        or item.name == ref
        or item.slug == _slugify(ref)
    ]
    if not candidates:
        raise LaunchError(f"Unknown project context: {ref}")
    if len(candidates) > 1:
        raise LaunchError(f"Ambiguous project context ref: {ref}")
    return candidates[0]


def rename_context(paths: ProjectPaths, ref: str, new_name: str) -> ProjectContextEntry:
    entries = load_contexts(paths)
    entry = resolve_context(paths, ref)
    new_slug = _slugify(new_name)
    _ensure_unique_context_identity(
        entries,
        name=new_name,
        slug=new_slug,
        ignore_id=entry.id,
    )
    updated = replace(
        entry,
        name=new_name,
        slug=new_slug,
        path=_relative_to_project(paths, paths.contexts_dir / f"{new_slug}.json"),
        updated_at=utc_now_iso(),
    )
    _replace_context(entries, updated, ref=entry.slug)
    save_contexts(paths, entries)
    if updated.path != entry.path:
        stale_path = paths.project_dir / entry.path
        if stale_path.exists():
            stale_path.unlink()
    return updated


def delete_context(paths: ProjectPaths, ref: str) -> ProjectContextEntry:
    entries = load_contexts(paths)
    entry = resolve_context(paths, ref)
    remaining = [item for item in entries if item.id != entry.id]
    save_contexts(paths, remaining)
    context_path = paths.project_dir / entry.path
    if context_path.exists():
        context_path.unlink()
    return entry


def _replace_context(
    entries: list[ProjectContextEntry],
    updated: ProjectContextEntry,
    *,
    ref: str | None = None,
) -> None:
    target = ref or updated.id
    for index, item in enumerate(entries):
        if item.id == target or item.slug == target:
            entries[index] = updated
            return
    raise LaunchError(f"Unknown project context: {target}")


def _ensure_unique_context_identity(
    entries: list[ProjectContextEntry],
    *,
    name: str,
    slug: str,
    ignore_id: str | None = None,
) -> None:
    for item in entries:
        if ignore_id is not None and item.id == ignore_id:
            continue
        if item.name == name:
            raise LaunchError(f"Project context already exists with name: {name}")
        if item.slug == slug:
            raise LaunchError(f"Project context already exists with slug: {slug}")


def _context_summary(
    *,
    memory_refs: tuple[str, ...],
    file_refs: tuple[str, ...],
    directory_refs: tuple[str, ...],
    item_refs: tuple[str, ...],
    inline_texts: tuple[str, ...],
    loop_latest_refs: tuple[str, ...],
) -> str:
    parts = [
        f"memories={len(memory_refs)}",
        f"files={len(file_refs)}",
        f"dirs={len(directory_refs)}",
        f"items={len(item_refs)}",
        f"inline={len(inline_texts)}",
        f"loop={len(loop_latest_refs)}",
    ]
    return ", ".join(parts)
