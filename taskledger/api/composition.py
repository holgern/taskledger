from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from taskledger.api.types import (
    ComposedBundle,
    ContextSource,
    ExpandedSelection,
    FileRenderMode,
    SourceBudget,
)
from taskledger.context import build_context_sources as _build_context_sources
from taskledger.context import compose_context_bundle as _compose_context_bundle
from taskledger.context import expand_selection as _expand_selection
from taskledger.storage import load_project_state

_INPUT_KEYS = (
    "context_inputs",
    "memory_inputs",
    "file_inputs",
    "directory_inputs",
    "item_inputs",
    "inline_inputs",
    "loop_artifact_inputs",
)


@dataclass(slots=True, frozen=True)
class SelectionRequest:
    context_names: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    file_refs: tuple[str, ...] = ()
    directory_refs: tuple[str, ...] = ()
    item_refs: tuple[str, ...] = ()
    inline_texts: tuple[str, ...] = ()
    loop_latest_refs: tuple[str, ...] = ()
    include_item_memories: bool = True
    file_render_mode: FileRenderMode = "content"

    def to_dict(self) -> dict[str, object]:
        return {
            "context_names": list(self.context_names),
            "memory_refs": list(self.memory_refs),
            "file_refs": list(self.file_refs),
            "directory_refs": list(self.directory_refs),
            "item_refs": list(self.item_refs),
            "inline_texts": list(self.inline_texts),
            "loop_latest_refs": list(self.loop_latest_refs),
            "include_item_memories": self.include_item_memories,
            "file_render_mode": self.file_render_mode,
        }


def expand_selection(
    workspace_root: Path, request: SelectionRequest
) -> ExpandedSelection:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    expanded = _expand_selection(
        state,
        context_names=request.context_names,
        memory_refs=request.memory_refs,
        file_refs=request.file_refs,
        directory_refs=request.directory_refs,
        item_refs=request.item_refs,
        inline_texts=request.inline_texts,
        loop_latest_refs=request.loop_latest_refs,
        file_render_mode=request.file_render_mode,
    )
    return ExpandedSelection(
        context_inputs=expanded["context_inputs"],
        memory_inputs=expanded["memory_inputs"],
        file_inputs=expanded["file_inputs"],
        directory_inputs=expanded["directory_inputs"],
        item_inputs=expanded["item_inputs"],
        inline_inputs=expanded["inline_inputs"],
        loop_artifact_inputs=expanded["loop_artifact_inputs"],
        file_render_mode=request.file_render_mode,
    )


def build_sources(
    workspace_root: Path,
    selection: ExpandedSelection,
    *,
    default_context_order: tuple[str, ...] = (),
    include_item_memories: bool = True,
    file_render_mode: FileRenderMode | None = None,
    source_budget: SourceBudget | None = None,
) -> tuple[ContextSource, ...]:
    state = load_project_state(workspace_root, recent_runs_limit=0)
    bounded_sources = _build_context_sources(
        state,
        memory_refs=selection.memory_inputs,
        file_refs=selection.file_inputs,
        directory_refs=selection.directory_inputs,
        item_refs=selection.item_inputs,
        inline_texts=selection.inline_inputs,
        loop_latest_refs=selection.loop_artifact_inputs,
        context_order=default_context_order,
        include_item_memories=include_item_memories,
        file_render_mode=file_render_mode or selection.file_render_mode,
        source_budget=(source_budget or SourceBudget()).to_project_source_budget(),
    )
    return tuple(ContextSource.from_model(source) for source in bounded_sources)


def compose_bundle(prompt: str, sources: tuple[ContextSource, ...]) -> ComposedBundle:
    model_bundle = _compose_context_bundle(
        prompt=prompt,
        sources=tuple(source.to_model() for source in sources),
    )
    return ComposedBundle(
        prompt=prompt,
        sources=sources,
        composed_text=model_bundle.composed_text,
        repo_refs=repo_refs_for_sources(sources),
        content_hash=model_bundle.content_hash,
    )


def describe_sources(sources: tuple[ContextSource, ...]) -> list[dict[str, object]]:
    return [source.to_dict() for source in sources]


def repo_refs_for_sources(sources: tuple[ContextSource, ...]) -> tuple[str, ...]:
    refs: list[str] = []
    for source in sources:
        repo_ref = source.repo_ref
        if repo_ref is None and source.metadata is not None:
            repo_value = source.metadata.get("repo")
            repo_ref = repo_value if isinstance(repo_value, str) else None
        if repo_ref is None or repo_ref in refs:
            continue
        refs.append(repo_ref)
    return tuple(refs)


def build_compose_payload(
    *,
    context_name: str | None,
    prompt: str | None,
    explicit_inputs: Mapping[str, tuple[str, ...]],
    file_render_mode: FileRenderMode = "content",
    selected_repo_refs: tuple[str, ...],
    run_in_repo: str | None,
    source_budget: SourceBudget,
    bundle: ComposedBundle,
) -> dict[str, object]:
    normalized_inputs = _normalize_explicit_inputs(explicit_inputs)
    warnings = _compose_warnings(bundle.sources)
    payload = {
        "kind": "project_compose",
        "project": {
            "context_name": context_name,
            "prompt": prompt,
            "repo_refs": list(selected_repo_refs),
            "run_in_repo": run_in_repo,
            "file_render_mode": file_render_mode,
            "source_budget": source_budget.to_dict(),
            "context_inputs": list(normalized_inputs["context_inputs"]),
            "memory_inputs": list(normalized_inputs["memory_inputs"]),
            "file_inputs": list(normalized_inputs["file_inputs"]),
            "directory_inputs": list(normalized_inputs["directory_inputs"]),
            "item_inputs": list(normalized_inputs["item_inputs"]),
            "inline_inputs": list(normalized_inputs["inline_inputs"]),
            "loop_artifact_inputs": list(normalized_inputs["loop_artifact_inputs"]),
            "source_summary": _compose_source_summary(bundle.sources),
            "warnings": warnings,
            "truncation_notes": warnings,
            "sources": describe_sources(bundle.sources),
            "composed_prompt": bundle.composed_text,
            "total_prompt_chars": len(bundle.composed_text),
            "context_hash": bundle.content_hash,
        },
    }
    return payload


def _normalize_explicit_inputs(
    explicit_inputs: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for key in _INPUT_KEYS:
        value = explicit_inputs.get(key, ())
        normalized[key] = tuple(value)
    return normalized


def _compose_source_summary(sources: tuple[ContextSource, ...]) -> dict[str, object]:
    by_kind: dict[str, int] = {}
    by_repo: dict[str, int] = {}
    for source in sources:
        by_kind[source.kind] = by_kind.get(source.kind, 0) + 1
        repo_ref = source.repo_ref
        if repo_ref is None and source.metadata is not None:
            repo_value = source.metadata.get("repo")
            repo_ref = repo_value if isinstance(repo_value, str) else None
        if repo_ref is None:
            continue
        by_repo[repo_ref] = by_repo.get(repo_ref, 0) + 1
    return {
        "total": len(sources),
        "by_kind": by_kind,
        "by_repo": by_repo,
    }


def _compose_warnings(sources: tuple[ContextSource, ...]) -> list[str]:
    warnings: list[str] = []
    for source in sources:
        if source.metadata is None:
            continue
        notice = source.metadata.get("truncation_notice")
        if isinstance(notice, str):
            warnings.append(f"{source.title or source.ref or source.kind}: {notice}")
    return warnings


__all__ = [
    "ComposedBundle",
    "ContextSource",
    "ExpandedSelection",
    "SelectionRequest",
    "SourceBudget",
    "build_compose_payload",
    "build_sources",
    "compose_bundle",
    "describe_sources",
    "expand_selection",
    "repo_refs_for_sources",
]
