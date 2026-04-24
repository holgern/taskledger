from __future__ import annotations

from typing import cast
from pathlib import Path

from taskledger.api.items import build_item_work_prompt, item_memory_refs, item_summary
from taskledger.api.types import ContextEntry, WorkItem
from taskledger.context import describe_context_sources as _describe_context_sources
from taskledger.storage import delete_context as _delete_context
from taskledger.storage import load_contexts as _load_contexts
from taskledger.storage import load_project_state, resolve_work_item
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


def build_context_for_item(
    workspace_root: Path,
    item_ref: str,
    *,
    include_runs: bool = True,
    include_validation: bool = True,
    save_as: str | None = None,
) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    item = resolve_work_item(state.paths, item_ref)
    summary = item_summary(workspace_root, item.id)
    work_prompt = build_item_work_prompt(workspace_root, item.id)
    memory_ref_payload = item_memory_refs(workspace_root, item.id)
    memory_refs = _context_memory_refs(item, memory_ref_payload)
    recent_runs = summary["recent_runs"] if include_runs else []
    validation_records = summary["validation_records"] if include_validation else []
    context_name = save_as or f"{item.slug}-working"
    inline_texts = _context_inline_texts(
        summary=summary,
        work_prompt=work_prompt,
        include_runs=include_runs,
        include_validation=include_validation,
    )
    entry = _save_context(
        state.paths,
        name=context_name,
        memory_refs=memory_refs,
        item_refs=(item.id,),
        inline_texts=inline_texts,
    )
    described = _describe_context_sources(
        state,
        memory_refs=memory_refs,
        item_refs=(item.id,),
        inline_texts=inline_texts,
        include_item_memories=True,
    )
    sources = described.get("sources")
    sources = sources if isinstance(sources, tuple) else tuple(cast(tuple[object, ...] | list[object], sources) or ())
    source_summary = _source_summary(sources)
    item_payload = summary["item"]
    assert isinstance(item_payload, dict)
    return {
        "context": {"id": entry.id, "name": entry.name},
        "item_ref": item.slug,
        "sources": {
            "item_refs": [item.id],
            "memory_refs": list(memory_refs),
            "repo_refs": list(cast(list[str], item_payload["repo_refs"])),
            "run_refs": [str(run["id"]) for run in recent_runs],  # type: ignore[attr-defined]
            "validation_refs": [str(record["id"]) for record in validation_records],  # type: ignore[attr-defined]
            "context_refs": list(cast(list[str], summary.get("context_refs", []))),
        },
        "bundle_summary": {
            "source_count": len(sources),
            "duplicates_removed": list(cast(tuple[object, ...], described.get("duplicates_removed", ()))),
            "has_prompt_seed": bool(work_prompt["prompt"]),
            "by_kind": source_summary,
        },
    }


def _context_memory_refs(
    item: WorkItem,
    memory_ref_payload: dict[str, str | None],
) -> tuple[str, ...]:
    refs: list[str] = []
    for ref in memory_ref_payload.values():
        if ref is None or ref in refs:
            continue
        refs.append(ref)
    for ref in item.linked_memories:
        if ref not in refs:
            refs.append(ref)
    return tuple(refs)


def _context_inline_texts(
    *,
    summary: dict[str, object],
    work_prompt: dict[str, object],
    include_runs: bool,
    include_validation: bool,
) -> tuple[str, ...]:
    item = summary["item"]
    assert isinstance(item, dict)
    inline_texts = [
        work_prompt["prompt"],
        "\n".join(
            [
                "Item execution hints:",
                f"- target repo: {item.get('target_repo_ref') or '-'}",
                f"- save target: {work_prompt.get('save_target_ref') or '-'}",
            ]
        ),
    ]
    if include_runs:
        run_lines = ["Recent runs:"]
        for run in cast(list[object], summary["recent_runs"]):
            assert isinstance(run, dict)
            run_lines.append(
                f"- {run.get('id')}  {run.get('status')}  "
                f"stage={run.get('stage') or '-'}"
            )
        if len(run_lines) > 1:
            inline_texts.append("\n".join(run_lines))
    if include_validation:
        validation_lines = ["Validation records:"]
        for record in cast(list[object], summary["validation_records"]):
            assert isinstance(record, dict)
            validation_lines.append(
                f"- {record.get('id')}  {record.get('status')}  "
                f"kind={record.get('kind')}"
            )
        if len(validation_lines) > 1:
            inline_texts.append("\n".join(validation_lines))
    context_refs = summary.get("context_refs")
    if isinstance(context_refs, list) and context_refs:
        inline_texts.append(
            "Related contexts:\n" + "\n".join(f"- {ref}" for ref in context_refs)
        )
    return tuple(
        text for text in inline_texts if isinstance(text, str) and text.strip()
    )


def _source_summary(sources: tuple[object, ...]) -> dict[str, int]:
    by_kind: dict[str, int] = {}
    for source in sources:
        kind = getattr(source, "kind", None)
        if not isinstance(kind, str):
            continue
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return by_kind
