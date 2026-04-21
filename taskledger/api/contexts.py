from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectContextEntry
from taskledger.storage import (
    delete_context as _delete_context,
)
from taskledger.storage import (
    load_contexts as _load_contexts,
)
from taskledger.storage import (
    load_project_state,
)
from taskledger.storage import (
    rename_context as _rename_context,
)
from taskledger.storage import (
    resolve_context as _resolve_context,
)
from taskledger.storage import (
    save_context as _save_context,
)
from taskledger.storage import (
    save_context_entry as _save_context_entry,
)
from taskledger.storage import (
    save_contexts as _save_contexts,
)


def delete_context(paths, ref: str) -> ProjectContextEntry:
    return _delete_context(paths, ref)


def load_contexts(paths) -> list[ProjectContextEntry]:
    return _load_contexts(paths)


def rename_context(paths, ref: str, new_name: str) -> ProjectContextEntry:
    return _rename_context(paths, ref, new_name)


def resolve_context(paths, ref: str) -> ProjectContextEntry:
    return _resolve_context(paths, ref)


def save_context(
    paths,
    *,
    name: str,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
) -> ProjectContextEntry:
    return _save_context(
        paths,
        name=name,
        memory_refs=memory_refs,
        file_refs=file_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
    )


def save_context_entry(paths, entry: ProjectContextEntry) -> ProjectContextEntry:
    return _save_context_entry(paths, entry)


def save_contexts(paths, entries: list[ProjectContextEntry]) -> None:
    _save_contexts(paths, entries)


def create_context_entry(
    workspace_root: Path,
    *,
    name: str,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
) -> ProjectContextEntry:
    return save_context(
        load_project_state(workspace_root).paths,
        name=name,
        memory_refs=memory_refs,
        file_refs=file_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
    )


def list_context_entries(workspace_root: Path) -> list[ProjectContextEntry]:
    return load_contexts(load_project_state(workspace_root).paths)


def show_context_entry(workspace_root: Path, ref: str) -> ProjectContextEntry:
    return resolve_context(load_project_state(workspace_root).paths, ref)


def rename_context_entry(
    workspace_root: Path, ref: str, *, new_name: str
) -> ProjectContextEntry:
    return rename_context(load_project_state(workspace_root).paths, ref, new_name)


def delete_context_entry(workspace_root: Path, ref: str) -> ProjectContextEntry:
    return delete_context(load_project_state(workspace_root).paths, ref)
