from __future__ import annotations

from pathlib import Path

from taskledger.api.types import ContextEntry
from taskledger.storage import delete_context as _delete_context
from taskledger.storage import load_contexts as _load_contexts
from taskledger.storage import load_project_state
from taskledger.storage import rename_context as _rename_context
from taskledger.storage import resolve_context as _resolve_context
from taskledger.storage import save_context as _save_context


def save_context(
    workspace_root: Path,
    *,
    name: str,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    directory_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
) -> ContextEntry:
    return _save_context(
        load_project_state(workspace_root).paths,
        name=name,
        memory_refs=memory_refs,
        file_refs=file_refs,
        directory_refs=directory_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
    )


def list_contexts(workspace_root: Path) -> list[ContextEntry]:
    return _load_contexts(load_project_state(workspace_root).paths)


def resolve_context(workspace_root: Path, ref: str) -> ContextEntry:
    return _resolve_context(load_project_state(workspace_root).paths, ref)


def rename_context(workspace_root: Path, ref: str, *, new_name: str) -> ContextEntry:
    return _rename_context(load_project_state(workspace_root).paths, ref, new_name)


def delete_context(workspace_root: Path, ref: str) -> ContextEntry:
    return _delete_context(load_project_state(workspace_root).paths, ref)


def create_context_entry(
    workspace_root: Path,
    *,
    name: str,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    directory_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
) -> ContextEntry:
    return save_context(
        workspace_root,
        name=name,
        memory_refs=memory_refs,
        file_refs=file_refs,
        directory_refs=directory_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
    )


def list_context_entries(workspace_root: Path) -> list[ContextEntry]:
    return list_contexts(workspace_root)


def show_context_entry(workspace_root: Path, ref: str) -> ContextEntry:
    return resolve_context(workspace_root, ref)


def rename_context_entry(
    workspace_root: Path, ref: str, *, new_name: str
) -> ContextEntry:
    return rename_context(workspace_root, ref, new_name=new_name)


def delete_context_entry(workspace_root: Path, ref: str) -> ContextEntry:
    return delete_context(workspace_root, ref)
