from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.ids import next_project_id as _next_id
from taskledger.ids import slugify_project_ref as _slugify
from taskledger.models import ProjectMemory, ProjectPaths
from taskledger.storage.common import content_hash as _content_hash
from taskledger.storage.common import merge_text as _merge_text
from taskledger.storage.common import summarize_text as _summarize_text
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
from taskledger.timeutils import utc_now_iso

_NUMERIC_SUFFIX_PATTERN = re.compile(r".*-(\d+)$")
_REQUIRED_MEMORY_KEYS = (
    "file_version",
    "id",
    "name",
    "slug",
    "path",
    "tags",
    "summary",
    "created_at",
    "updated_at",
    "source_run_id",
    "content_hash",
)


def load_memories(paths: ProjectPaths) -> list[ProjectMemory]:
    memories: list[ProjectMemory] = []
    for memory_file in _iter_markdown_files(paths.memories_dir):
        metadata, body = _read_markdown_front_matter(memory_file)
        _validate_required_keys(metadata, memory_file, label="memory")
        _validate_file_version(metadata, memory_file, label="memory")
        memory_id = _string_metadata_value(metadata, "id", path=memory_file)
        if memory_file.stem != memory_id:
            raise LaunchError(
                "Invalid memory document "
                f"{memory_file}: filename stem {memory_file.stem!r} does not "
                f"match front matter id {memory_id!r}."
            )
        expected_path = f"memories/{memory_id}.md"
        encoded_path = _string_metadata_value(metadata, "path", path=memory_file)
        if encoded_path != expected_path:
            raise LaunchError(
                "Invalid memory document "
                f"{memory_file}: front matter path must be {expected_path!r}."
            )
        payload = dict(metadata)
        payload["summary"] = _summarize_text(body)
        payload["content_hash"] = _content_hash(body)
        try:
            memories.append(ProjectMemory.from_dict(payload))
        except (TypeError, ValueError) as exc:
            raise LaunchError(
                f"Invalid memory front matter {memory_file}: {exc}"
            ) from exc
    memories.sort(key=lambda memory: _id_sort_key(memory.id))
    return memories


def save_memories(paths: ProjectPaths, memories: list[ProjectMemory]) -> None:
    keep_ids: set[str] = set()
    for memory in sorted(memories, key=lambda item: _id_sort_key(item.id)):
        memory_path = memory_markdown_path(paths, memory)
        body = ""
        if memory_path.exists():
            _, body = _read_markdown_front_matter(memory_path)
        _write_memory_document(paths, memory, body)
        keep_ids.add(memory.id)
    for stale_path in _iter_markdown_files(paths.memories_dir):
        if stale_path.stem in keep_ids:
            continue
        try:
            stale_path.unlink()
        except OSError as exc:
            raise LaunchError(
                f"Failed to delete memory file {stale_path}: {exc}"
            ) from exc


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
    body_text = body or ""
    now = utc_now_iso()
    memory = ProjectMemory(
        id=memory_id,
        name=name,
        slug=slug,
        path=f"memories/{memory_id}.md",
        tags=tuple(sorted(set(tags))),
        summary=_summarize_text(body_text),
        created_at=now,
        updated_at=now,
        source_run_id=source_run_id,
        content_hash=_content_hash(body_text),
    )
    _write_memory_document(paths, memory, body_text)
    return memory


def resolve_memory(paths: ProjectPaths, ref: str) -> ProjectMemory:
    return _resolve_memory_from_list(load_memories(paths), ref)


def read_memory_body(paths: ProjectPaths, memory: ProjectMemory) -> str:
    markdown_path = memory_markdown_path(paths, memory)
    if not markdown_path.exists():
        return ""
    _, body = _read_markdown_front_matter(markdown_path)
    return body


def refresh_memory(paths: ProjectPaths, ref: str) -> ProjectMemory:
    memories = load_memories(paths)
    memory = _resolve_memory_from_list(memories, ref)
    body = read_memory_body(paths, memory)
    updated = replace(
        memory,
        summary=_summarize_text(body),
        updated_at=utc_now_iso(),
        content_hash=_content_hash(body),
    )
    _write_memory_document(paths, updated, body)
    return updated


def write_memory_body(
    paths: ProjectPaths,
    ref: str,
    body: str,
    *,
    source_run_id: str | None = None,
) -> ProjectMemory:
    memory = resolve_memory(paths, ref)
    next_source_run_id = (
        source_run_id if source_run_id is not None else memory.source_run_id
    )
    updated = replace(
        memory,
        summary=_summarize_text(body),
        updated_at=utc_now_iso(),
        source_run_id=next_source_run_id,
        content_hash=_content_hash(body),
    )
    _write_memory_document(paths, updated, body)
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
    body = read_memory_body(paths, memory)
    updated = replace(memory, name=new_name, slug=slug, updated_at=utc_now_iso())
    _write_memory_document(paths, updated, body)
    return updated


def delete_memory(paths: ProjectPaths, ref: str) -> ProjectMemory:
    memory = resolve_memory(paths, ref)
    markdown_path = memory_markdown_path(paths, memory)
    if markdown_path.exists():
        try:
            markdown_path.unlink()
        except OSError as exc:
            raise LaunchError(
                f"Failed to delete memory file {markdown_path}: {exc}"
            ) from exc
    return memory


def update_memory_tags(
    paths: ProjectPaths,
    ref: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> ProjectMemory:
    memory = resolve_memory(paths, ref)
    tags = set(memory.tags)
    tags.update(tag for tag in add_tags if tag)
    tags.difference_update(tag for tag in remove_tags if tag)
    body = read_memory_body(paths, memory)
    updated = replace(
        memory,
        tags=tuple(sorted(tags)),
        updated_at=utc_now_iso(),
    )
    _write_memory_document(paths, updated, body)
    return updated


def memory_markdown_path(paths: ProjectPaths, memory: ProjectMemory) -> Path:
    return paths.memories_dir / f"{memory.id}.md"


def memory_body_path(paths: ProjectPaths, memory: ProjectMemory) -> Path:
    return memory_markdown_path(paths, memory)


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


def _id_sort_key(value: str) -> tuple[int, int, str]:
    match = _NUMERIC_SUFFIX_PATTERN.match(value)
    if match is None:
        return (1, 0, value)
    return (0, int(match.group(1)), value)


def _write_memory_document(
    paths: ProjectPaths, memory: ProjectMemory, body: str
) -> None:
    expected_path = f"memories/{memory.id}.md"
    if memory.path != expected_path:
        raise LaunchError(
            f"Invalid memory path for {memory.id}: expected {expected_path!r}."
        )
    normalized_tags = tuple(sorted(set(memory.tags)))
    normalized = replace(
        memory,
        tags=normalized_tags,
        summary=_summarize_text(body),
        content_hash=_content_hash(body),
    )
    _write_markdown_front_matter(
        memory_markdown_path(paths, normalized),
        {"file_version": MARKDOWN_FILE_VERSION, **normalized.to_dict()},
        body,
    )


def _string_metadata_value(metadata: dict[str, object], key: str, *, path: Path) -> str:
    value = metadata.get(key)
    if isinstance(value, str):
        return value
    raise LaunchError(
        f"Invalid memory front matter {path}: key {key!r} must be a string."
    )


def _validate_required_keys(
    metadata: dict[str, object], path: Path, *, label: str
) -> None:
    missing = [key for key in _REQUIRED_MEMORY_KEYS if key not in metadata]
    if not missing:
        return
    missing_text = ", ".join(missing)
    raise LaunchError(
        f"Invalid {label} front matter {path}: missing required keys: {missing_text}."
    )


def _validate_file_version(
    metadata: dict[str, object], path: Path, *, label: str
) -> None:
    value = metadata.get("file_version")
    if not isinstance(value, str):
        raise LaunchError(
            f"Invalid {label} front matter {path}: key 'file_version' must be a string."
        )
    if value != MARKDOWN_FILE_VERSION:
        raise LaunchError(
            f"Unsupported {label} file_version {value!r} in {path}; "
            f"expected {MARKDOWN_FILE_VERSION!r}."
        )
