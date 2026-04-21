from __future__ import annotations

from pathlib import Path

from taskledger.api.types import Memory
from taskledger.storage import create_memory as _create_memory
from taskledger.storage import delete_memory as _delete_memory
from taskledger.storage import load_memories as _load_memories
from taskledger.storage import load_project_state
from taskledger.storage import read_memory_body as _read_memory_body
from taskledger.storage import refresh_memory as _refresh_memory
from taskledger.storage import rename_memory as _rename_memory
from taskledger.storage import resolve_memory as _resolve_memory
from taskledger.storage import update_memory_body as _update_memory_body
from taskledger.storage import update_memory_tags as _update_memory_tags
from taskledger.storage import write_memory_body as _write_memory_body


def create_memory(
    workspace_root: Path,
    *,
    name: str,
    body: str | None = None,
    source_run_id: str | None = None,
) -> Memory:
    return _create_memory(
        load_project_state(workspace_root).paths,
        name=name,
        body=body,
        source_run_id=source_run_id,
    )


def list_memories(workspace_root: Path) -> list[Memory]:
    return _load_memories(load_project_state(workspace_root).paths)


def resolve_memory(workspace_root: Path, ref: str) -> Memory:
    return _resolve_memory(load_project_state(workspace_root).paths, ref)


def read_memory_body(workspace_root: Path, ref: str) -> str:
    paths = load_project_state(workspace_root).paths
    memory = _resolve_memory(paths, ref)
    return _read_memory_body(paths, memory)


def refresh_memory(workspace_root: Path, ref: str) -> Memory:
    return _refresh_memory(load_project_state(workspace_root).paths, ref)


def rename_memory(workspace_root: Path, ref: str, *, new_name: str) -> Memory:
    return _rename_memory(load_project_state(workspace_root).paths, ref, new_name)


def update_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    mode: str = "replace",
    source_run_id: str | None = None,
) -> Memory:
    return _update_memory_body(
        load_project_state(workspace_root).paths,
        ref,
        text,
        mode=mode,
        source_run_id=source_run_id,
    )


def write_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> Memory:
    return _write_memory_body(
        load_project_state(workspace_root).paths,
        ref,
        text,
        source_run_id=source_run_id,
    )


def update_memory_tags(
    workspace_root: Path,
    ref: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> Memory:
    return _update_memory_tags(
        load_project_state(workspace_root).paths,
        ref,
        add_tags=add_tags,
        remove_tags=remove_tags,
    )


def delete_memory(workspace_root: Path, ref: str) -> Memory:
    return _delete_memory(load_project_state(workspace_root).paths, ref)


def create_memory_entry(
    workspace_root: Path,
    *,
    name: str,
    body: str | None = None,
    source_run_id: str | None = None,
) -> Memory:
    return create_memory(
        workspace_root,
        name=name,
        body=body,
        source_run_id=source_run_id,
    )


def show_memory(workspace_root: Path, ref: str) -> Memory:
    return resolve_memory(workspace_root, ref)


def show_memory_with_body(workspace_root: Path, ref: str) -> tuple[Memory, str]:
    memory = resolve_memory(workspace_root, ref)
    return memory, read_memory_body(workspace_root, ref)


def rename_memory_entry(
    workspace_root: Path, ref: str, *, new_name: str
) -> tuple[Memory, str]:
    memory = rename_memory(workspace_root, ref, new_name=new_name)
    return memory, read_memory_body(workspace_root, memory.id)


def delete_memory_entry(workspace_root: Path, ref: str) -> Memory:
    return delete_memory(workspace_root, ref)


def retag_memory(
    workspace_root: Path,
    ref: str,
    *,
    add_tags: tuple[str, ...] = (),
    remove_tags: tuple[str, ...] = (),
) -> tuple[Memory, str]:
    memory = update_memory_tags(
        workspace_root,
        ref,
        add_tags=add_tags,
        remove_tags=remove_tags,
    )
    return memory, read_memory_body(workspace_root, memory.id)


def replace_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> tuple[Memory, str]:
    memory = write_memory_body(
        workspace_root,
        ref,
        text,
        source_run_id=source_run_id,
    )
    return memory, read_memory_body(workspace_root, memory.id)


def append_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> tuple[Memory, str]:
    memory = update_memory_body(
        workspace_root,
        ref,
        text,
        mode="append",
        source_run_id=source_run_id,
    )
    return memory, read_memory_body(workspace_root, memory.id)


def prepend_memory_body(
    workspace_root: Path,
    ref: str,
    text: str,
    *,
    source_run_id: str | None = None,
) -> tuple[Memory, str]:
    memory = update_memory_body(
        workspace_root,
        ref,
        text,
        mode="prepend",
        source_run_id=source_run_id,
    )
    return memory, read_memory_body(workspace_root, memory.id)
