from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.ids import slugify_project_ref as _slugify
from taskledger.models import ProjectMemory, ProjectPaths, utc_now_iso
from taskledger.storage.common import content_hash as _content_hash
from taskledger.storage.common import load_json_array as _load_json_array
from taskledger.storage.common import merge_text as _merge_text
from taskledger.storage.common import read_text as _read_text
from taskledger.storage.common import (
    relative_to_project as _relative_to_project,
)
from taskledger.storage.common import summarize_text as _summarize_text
from taskledger.storage.common import write_json as _write_json
from taskledger.storage.common import write_text as _write_text


def load_memories(paths: ProjectPaths) -> list[ProjectMemory]:
    return [
        ProjectMemory.from_dict(item)
        for item in _load_json_array(paths.memory_index_path, "memory index")
    ]


def save_memories(paths: ProjectPaths, memories: list[ProjectMemory]) -> None:
    _write_json(paths.memory_index_path, [item.to_dict() for item in memories])


def create_memory(
    paths: ProjectPaths,
    *,
    name: str,
    body: str | None = None,
    tags: tuple[str, ...] = (),
    source_run_id: str | None = None,
) -> ProjectMemory:
    memories = load_memories(paths)
    slug = _slugify(name)
    _ensure_unique_memory_identity(memories, name=name, slug=slug)
    memory_id = _next_id("mem", [item.id for item in memories])
    memory_path = paths.memories_dir / f"{memory_id}.md"
    body_text = body or ""
    if body_text.strip():
        _write_text(memory_path, body_text)
    now = utc_now_iso()
    memory = ProjectMemory(
        id=memory_id,
        name=name,
        slug=slug,
        path=_relative_to_project(paths, memory_path),
        tags=tuple(sorted(set(tags))),
        summary=_summarize_text(body_text),
        created_at=now,
        updated_at=now,
        source_run_id=source_run_id,
        content_hash=_content_hash(body_text),
    )
    memories.append(memory)
    save_memories(paths, memories)
    return memory


def resolve_memory(paths: ProjectPaths, ref: str) -> ProjectMemory:
    return _resolve_memory_from_list(load_memories(paths), ref)


def read_memory_body(paths: ProjectPaths, memory: ProjectMemory) -> str:
    body_path = memory_body_path(paths, memory)
    if not body_path.exists():
        return ""
    return _read_text(body_path)


def refresh_memory(paths: ProjectPaths, ref: str) -> ProjectMemory:
    memories = load_memories(paths)
    memory = _resolve_memory_from_list(memories, ref)
    body = _read_text(memory_body_path(paths, memory))
    updated = replace(
        memory,
        summary=_summarize_text(body),
        updated_at=utc_now_iso(),
        content_hash=_content_hash(body),
    )
    _replace_memory(memories, updated)
    save_memories(paths, memories)
    return updated


def write_memory_body(
    paths: ProjectPaths,
    ref: str,
    body: str,
    *,
    source_run_id: str | None = None,
) -> ProjectMemory:
    memories = load_memories(paths)
    memory = _resolve_memory_from_list(memories, ref)
    body_path = memory_body_path(paths, memory)
    if body.strip():
        _write_text(body_path, body)
    elif body_path.exists():
        try:
            body_path.unlink()
        except OSError as exc:
            raise LaunchError(
                f"Failed to delete memory file {body_path}: {exc}"
            ) from exc
    updated = replace(
        memory,
        summary=_summarize_text(body),
        updated_at=utc_now_iso(),
        source_run_id=source_run_id,
        content_hash=_content_hash(body),
    )
    _replace_memory(memories, updated)
    save_memories(paths, memories)
    return updated


def update_memory_body(
    paths: ProjectPaths,
    ref: str,
    text: str,
    *,
    mode: str,
    source_run_id: str | None = None,
) -> ProjectMemory:
    memory = resolve_memory(paths, ref)
    current = read_memory_body(paths, memory)
    if mode == "replace":
        next_body = text
    elif mode == "append":
        next_body = _merge_text(current, text, prepend=False)
    elif mode == "prepend":
        next_body = _merge_text(current, text, prepend=True)
    else:
        raise LaunchError(f"Unsupported memory update mode: {mode}")
    return write_memory_body(
        paths,
        memory.id,
        next_body,
        source_run_id=source_run_id,
    )


def rename_memory(paths: ProjectPaths, ref: str, new_name: str) -> ProjectMemory:
    memories = load_memories(paths)
    memory = _resolve_memory_from_list(memories, ref)
    slug = _slugify(new_name)
    _ensure_unique_memory_identity(
        memories,
        name=new_name,
        slug=slug,
        ignore_id=memory.id,
    )
    updated = replace(memory, name=new_name, slug=slug, updated_at=utc_now_iso())
    _replace_memory(memories, updated)
    save_memories(paths, memories)
    return updated


def delete_memory(paths: ProjectPaths, ref: str) -> ProjectMemory:
    memories = load_memories(paths)
    memory = _resolve_memory_from_list(memories, ref)
    remaining = [item for item in memories if item.id != memory.id]
    save_memories(paths, remaining)
    body_path = memory_body_path(paths, memory)
    if body_path.exists():
        try:
            body_path.unlink()
        except OSError as exc:
            raise LaunchError(
                f"Failed to delete memory file {body_path}: {exc}"
            ) from exc
    return memory


def update_memory_tags(
    paths: ProjectPaths,
    ref: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> ProjectMemory:
    memories = load_memories(paths)
    memory = _resolve_memory_from_list(memories, ref)
    tags = set(memory.tags)
    tags.update(tag for tag in add_tags if tag)
    tags.difference_update(tag for tag in remove_tags if tag)
    updated = replace(memory, tags=tuple(sorted(tags)), updated_at=utc_now_iso())
    _replace_memory(memories, updated)
    save_memories(paths, memories)
    return updated


def memory_body_path(paths: ProjectPaths, memory: ProjectMemory) -> Path:
    return paths.project_dir / memory.path


def _replace_memory(memories: list[ProjectMemory], updated: ProjectMemory) -> None:
    for index, item in enumerate(memories):
        if item.id == updated.id:
            memories[index] = updated
            return
    raise LaunchError(f"Unknown project memory: {updated.id}")


def _resolve_memory_from_list(memories: list[ProjectMemory], ref: str) -> ProjectMemory:
    normalized_ref = _slugify(ref)
    candidates = [
        item
        for item in memories
        if item.id == ref
        or item.slug == ref
        or item.name == ref
        or item.slug == normalized_ref
    ]
    unique_candidates: list[ProjectMemory] = []
    seen: set[str] = set()
    for item in candidates:
        if item.id in seen:
            continue
        unique_candidates.append(item)
        seen.add(item.id)
    if not unique_candidates:
        raise LaunchError(f"Unknown project memory: {ref}")
    if len(unique_candidates) > 1:
        raise LaunchError(f"Ambiguous project memory ref: {ref}")
    return unique_candidates[0]


def _ensure_unique_memory_identity(
    memories: list[ProjectMemory],
    *,
    name: str,
    slug: str,
    ignore_id: str | None = None,
) -> None:
    for item in memories:
        if ignore_id is not None and item.id == ignore_id:
            continue
        if item.name == name:
            raise LaunchError(f"Project memory already exists with name: {name}")
        if item.slug == slug:
            raise LaunchError(f"Project memory already exists with slug: {slug}")
