from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectMemory
from taskledger.storage import (
    create_memory as _create_memory,
)
from taskledger.storage import (
    delete_memory as _delete_memory,
)
from taskledger.storage import (
    load_memories as _load_memories,
)
from taskledger.storage import (
    load_project_state,
)
from taskledger.storage import (
    memory_body_path as _memory_body_path,
)
from taskledger.storage import (
    read_memory_body as _read_memory_body,
)
from taskledger.storage import (
    refresh_memory as _refresh_memory,
)
from taskledger.storage import (
    rename_memory as _rename_memory,
)
from taskledger.storage import (
    resolve_memory as _resolve_memory,
)
from taskledger.storage import (
    save_memories as _save_memories,
)
from taskledger.storage import (
    update_memory_body as _update_memory_body,
)
from taskledger.storage import (
    update_memory_tags as _update_memory_tags,
)
from taskledger.storage import (
    write_memory_body as _write_memory_body,
)


def create_memory(paths, **kwargs) -> ProjectMemory:
    return _create_memory(paths, **kwargs)


def delete_memory(paths, ref: str) -> ProjectMemory:
    return _delete_memory(paths, ref)


def load_memories(paths) -> list[ProjectMemory]:
    return _load_memories(paths)


def memory_body_path(paths, memory: ProjectMemory):
    return _memory_body_path(paths, memory)


def read_memory_body(paths, memory: ProjectMemory) -> str:
    return _read_memory_body(paths, memory)


def refresh_memory(paths, ref: str) -> ProjectMemory:
    return _refresh_memory(paths, ref)


def rename_memory(paths, ref: str, new_name: str) -> ProjectMemory:
    return _rename_memory(paths, ref, new_name)


def resolve_memory(paths, ref: str) -> ProjectMemory:
    return _resolve_memory(paths, ref)


def save_memories(paths, memories: list[ProjectMemory]) -> None:
    _save_memories(paths, memories)


def update_memory_body(
    paths,
    ref: str,
    text: str,
    *,
    mode="replace",
    source_run_id=None,
):
    return _update_memory_body(
        paths,
        ref,
        text,
        mode=mode,
        source_run_id=source_run_id,
    )


def update_memory_tags(
    paths,
    ref: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> ProjectMemory:
    return _update_memory_tags(paths, ref, add_tags=add_tags, remove_tags=remove_tags)


def write_memory_body(
    paths,
    ref: str,
    text: str,
    *,
    source_run_id=None,
) -> ProjectMemory:
    return _write_memory_body(paths, ref, text, source_run_id=source_run_id)


def create_memory_entry(
    workspace_root: Path,
    *,
    name: str,
    body: str | None = None,
    source_run_id: str | None = None,
) -> ProjectMemory:
    return create_memory(
        load_project_state(workspace_root).paths,
        name=name,
        body=body,
        source_run_id=source_run_id,
    )


def list_memories(workspace_root: Path) -> list[ProjectMemory]:
    return load_memories(load_project_state(workspace_root).paths)


def show_memory(workspace_root: Path, ref: str) -> ProjectMemory:
    return resolve_memory(load_project_state(workspace_root).paths, ref)


def show_memory_with_body(workspace_root: Path, ref: str) -> tuple[ProjectMemory, str]:
    paths = load_project_state(workspace_root).paths
    memory = resolve_memory(paths, ref)
    return memory, read_memory_body(paths, memory)


def rename_memory_entry(
    workspace_root: Path, ref: str, *, new_name: str
) -> tuple[ProjectMemory, str]:
    paths = load_project_state(workspace_root).paths
    memory = rename_memory(paths, ref, new_name)
    return memory, read_memory_body(paths, memory)


def delete_memory_entry(workspace_root: Path, ref: str) -> ProjectMemory:
    return delete_memory(load_project_state(workspace_root).paths, ref)


def retag_memory(
    workspace_root: Path,
    ref: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> tuple[ProjectMemory, str]:
    paths = load_project_state(workspace_root).paths
    memory = update_memory_tags(paths, ref, add_tags=add_tags, remove_tags=remove_tags)
    return memory, read_memory_body(paths, memory)


def replace_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> tuple[ProjectMemory, str]:
    paths = load_project_state(workspace_root).paths
    memory = write_memory_body(paths, ref, text, source_run_id=source_run_id)
    return memory, read_memory_body(paths, memory)


def append_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> tuple[ProjectMemory, str]:
    paths = load_project_state(workspace_root).paths
    memory = update_memory_body(
        paths,
        ref,
        text,
        mode="append",
        source_run_id=source_run_id,
    )
    return memory, read_memory_body(paths, memory)


def prepend_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> tuple[ProjectMemory, str]:
    paths = load_project_state(workspace_root).paths
    memory = update_memory_body(
        paths,
        ref,
        text,
        mode="prepend",
        source_run_id=source_run_id,
    )
    return memory, read_memory_body(paths, memory)
