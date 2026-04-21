from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.models import (
    ContextBundle,
    ContextSource,
    ProjectSourceBudget,
    ProjectState,
    ProjectWorkItem,
)
from taskledger.storage import (
    read_memory_body,
    resolve_context,
    resolve_memory,
    resolve_repo,
    resolve_repo_root,
    resolve_work_item,
)

_KNOWN_CONTEXT_KINDS = ("memory", "file", "item", "inline", "loop_artifact")


def expand_selection(
    state: ProjectState,
    *,
    context_names: tuple[str, ...] = (),
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
) -> dict[str, tuple[str, ...]]:
    expanded_memory_refs = list(memory_refs)
    expanded_file_refs = list(file_refs)
    expanded_item_refs = list(item_refs)
    expanded_inline_texts = list(inline_texts)
    expanded_loop_latest_refs = list(loop_latest_refs)
    expanded_context_names = list(context_names)
    for context_name in context_names:
        entry = resolve_context(state.paths, context_name)
        expanded_memory_refs.extend(entry.memory_refs)
        expanded_file_refs.extend(entry.file_refs)
        expanded_item_refs.extend(entry.item_refs)
        expanded_inline_texts.extend(entry.inline_texts)
        expanded_loop_latest_refs.extend(entry.loop_latest_refs)
    return {
        "context_inputs": tuple(expanded_context_names),
        "memory_inputs": tuple(expanded_memory_refs),
        "file_inputs": tuple(expanded_file_refs),
        "item_inputs": tuple(expanded_item_refs),
        "inline_inputs": tuple(expanded_inline_texts),
        "loop_artifact_inputs": tuple(expanded_loop_latest_refs),
    }


def build_context_sources(
    state: ProjectState,
    *,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
    context_order: tuple[str, ...] = (),
    source_budget: ProjectSourceBudget | None = None,
) -> tuple[ContextSource, ...]:
    ordered_sources = _collect_context_sources(
        state,
        memory_refs=memory_refs,
        file_refs=file_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
        context_order=context_order,
    )
    deduped_sources, _ = _dedupe_sources(ordered_sources)
    return _apply_source_budget(
        tuple(deduped_sources), source_budget or ProjectSourceBudget()
    )


def describe_context_sources(
    state: ProjectState,
    *,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
    context_order: tuple[str, ...] = (),
    source_budget: ProjectSourceBudget | None = None,
) -> dict[str, object]:
    ordered_sources = _collect_context_sources(
        state,
        memory_refs=memory_refs,
        file_refs=file_refs,
        item_refs=item_refs,
        inline_texts=inline_texts,
        loop_latest_refs=loop_latest_refs,
        context_order=context_order,
    )
    deduped_sources, duplicates_removed = _dedupe_sources(ordered_sources)
    bounded_sources = _apply_source_budget(
        tuple(deduped_sources), source_budget or ProjectSourceBudget()
    )
    return {
        "sources": bounded_sources,
        "expansion_order": [_source_display_ref(source) for source in ordered_sources],
        "duplicates_removed": duplicates_removed,
    }


def resolve_project_file_ref(
    state: ProjectState, ref: str
) -> tuple[Path, str, dict[str, object]]:
    return _resolve_file_source(state, ref)


def _collect_context_sources(
    state: ProjectState,
    *,
    memory_refs: tuple[str, ...] = (),
    file_refs: tuple[str, ...] = (),
    item_refs: tuple[str, ...] = (),
    inline_texts: tuple[str, ...] = (),
    loop_latest_refs: tuple[str, ...] = (),
    context_order: tuple[str, ...] = (),
) -> tuple[ContextSource, ...]:
    ordered_kinds = _ordered_context_kinds(context_order)
    sources_by_kind: dict[str, list[ContextSource]] = {
        "memory": [],
        "file": [],
        "item": [],
        "inline": [],
        "loop_artifact": [],
    }

    for ref in memory_refs:
        memory = resolve_memory(state.paths, ref)
        body = read_memory_body(state.paths, memory)
        sources_by_kind["memory"].append(
            ContextSource(
                kind="memory",
                ref=memory.id,
                title=f"{memory.id} ({memory.slug})",
                body=body,
                metadata={
                    "name": memory.name,
                    "slug": memory.slug,
                    "tags": list(memory.tags),
                    "summary": memory.summary,
                    "path": memory.path,
                },
            )
        )

    for ref in file_refs:
        file_path, title, metadata = _resolve_file_source(state, ref)
        sources_by_kind["file"].append(
            ContextSource(
                kind="file",
                ref=ref,
                title=title,
                body=_read_text(file_path),
                metadata=metadata,
            )
        )

    for ref in item_refs:
        item = resolve_work_item(state.paths, ref)
        sources_by_kind["item"].append(_item_source(item))
        for memory_ref in (
            item.analysis_memory_ref,
            item.state_memory_ref,
            item.plan_memory_ref,
            item.implementation_memory_ref,
            item.validation_memory_ref,
        ):
            if memory_ref is None:
                continue
            memory = resolve_memory(state.paths, memory_ref)
            sources_by_kind["memory"].append(
                ContextSource(
                    kind="memory",
                    ref=memory.id,
                    title=f"{memory.id} ({memory.slug})",
                    body=read_memory_body(state.paths, memory),
                    metadata={
                        "name": memory.name,
                        "slug": memory.slug,
                        "tags": list(memory.tags),
                        "summary": memory.summary,
                        "path": memory.path,
                        "from_item": item.id,
                    },
                )
            )
        for file_ref in item.discovered_file_refs:
            file_path, title, metadata = _resolve_file_source(state, file_ref)
            metadata = {**metadata, "from_item": item.id}
            sources_by_kind["file"].append(
                ContextSource(
                    kind="file",
                    ref=file_ref,
                    title=title,
                    body=_read_text(file_path),
                    metadata=metadata,
                )
            )

    for index, text in enumerate(inline_texts, start=1):
        sources_by_kind["inline"].append(
            ContextSource(
                kind="inline",
                ref=f"inline-{index}",
                title=f"Inline note {index}",
                body=text,
            )
        )

    for ref in loop_latest_refs:
        artifact_path = _resolve_external_artifact_file(state, ref)
        sources_by_kind["loop_artifact"].append(
            ContextSource(
                kind="loop_artifact",
                ref=ref,
                title=str(artifact_path.relative_to(state.paths.workspace_root)),
                body=_read_text(artifact_path),
                metadata={"path": str(artifact_path)},
            )
        )

    ordered_sources: list[ContextSource] = []
    for kind in ordered_kinds:
        ordered_sources.extend(sources_by_kind[kind])
    return tuple(ordered_sources)


def compose_context_bundle(
    *, prompt: str, sources: tuple[ContextSource, ...], name: str | None = None
) -> ContextBundle:
    lines: list[str] = []
    if sources:
        lines.extend(["# Project Context", ""])
        for source in sources:
            lines.append(_source_heading(source))
            if source.body:
                lines.append(source.body.rstrip())
            lines.append("")
    lines.append("# User Task")
    lines.append(prompt.rstrip())
    composed_text = "\n".join(lines).rstrip() + "\n"
    return ContextBundle(
        name=name,
        sources=sources,
        composed_text=composed_text,
        content_hash=sha256(composed_text.encode("utf-8")).hexdigest(),
    )


def default_item_plan_prompt(item: ProjectWorkItem) -> str:
    lines = [item.title]
    if item.description:
        lines.extend(["", item.description])
    if item.acceptance_criteria:
        lines.extend(["", "Acceptance criteria:"])
        lines.extend(f"- {criterion}" for criterion in item.acceptance_criteria)
    if item.depends_on:
        lines.extend(["", "Depends on:"])
        lines.extend(f"- {ref}" for ref in item.depends_on)
    if item.labels:
        lines.extend(["", "Labels:", ", ".join(item.labels)])
    if item.notes:
        lines.extend(["", "Notes:", item.notes])
    return "\n".join(lines).strip()


def _ordered_context_kinds(configured: tuple[str, ...]) -> tuple[str, ...]:
    selected: list[str] = []
    for kind in configured:
        if kind in _KNOWN_CONTEXT_KINDS and kind not in selected:
            selected.append(kind)
    for kind in _KNOWN_CONTEXT_KINDS:
        if kind not in selected:
            selected.append(kind)
    return tuple(selected)


def _dedupe_sources(
    sources: tuple[ContextSource, ...],
) -> tuple[tuple[ContextSource, ...], list[str]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[ContextSource] = []
    duplicates_removed: list[str] = []
    for source in sources:
        key = _source_identity_key(source)
        if key in seen:
            duplicates_removed.append(_source_display_ref(source))
            continue
        seen.add(key)
        deduped.append(source)
    return tuple(deduped), duplicates_removed


def _source_heading(source: ContextSource) -> str:
    title = source.title or source.ref
    if source.kind == "memory":
        return f"## Memory: {title}"
    if source.kind == "file":
        return f"## File: {title}"
    if source.kind == "item":
        return f"## Item: {title}"
    if source.kind == "loop_artifact":
        return f"## Artifact: {title}"
    return f"## Inline: {title}"


def _source_identity_key(source: ContextSource) -> tuple[str, str, str]:
    metadata = source.metadata or {}
    canonical_ref = metadata.get("path")
    if not isinstance(canonical_ref, str):
        canonical_ref = metadata.get("repo_relative_path")
    if not isinstance(canonical_ref, str):
        canonical_ref = source.ref
    return (
        source.kind,
        canonical_ref,
        sha256(source.body.encode("utf-8")).hexdigest(),
    )


def _source_display_ref(source: ContextSource) -> str:
    return f"{source.kind}:{source.title or source.ref}"


def _item_source(item: ProjectWorkItem) -> ContextSource:
    body_lines = [
        f"Title: {item.title}",
        f"Status: {item.status}",
        f"Stage: {item.stage}",
    ]
    if item.description:
        body_lines.extend(["", item.description])
    if item.acceptance_criteria:
        body_lines.extend(["", "Acceptance criteria:"])
        body_lines.extend(f"- {criterion}" for criterion in item.acceptance_criteria)
    if item.depends_on:
        body_lines.extend(["", "Depends on:"])
        body_lines.extend(f"- {ref}" for ref in item.depends_on)
    if item.labels:
        body_lines.extend(["", "Labels:", ", ".join(item.labels)])
    if item.notes:
        body_lines.extend(["", "Notes:", item.notes])
    return ContextSource(
        kind="item",
        ref=item.id,
        title=item.id,
        body="\n".join(body_lines).strip(),
        metadata={
            "title": item.title,
            "status": item.status,
            "stage": item.stage,
            "depends_on": list(item.depends_on),
            "labels": list(item.labels),
            "linked_memories": list(item.linked_memories),
            "linked_loop_tasks": list(item.linked_loop_tasks),
            "linked_runs": list(item.linked_runs),
            "save_target_ref": item.save_target_ref,
        },
    )


def _resolve_file_source(
    state: ProjectState, ref: str
) -> tuple[Path, str, dict[str, object]]:
    repo_prefix, repo_relative_path = _split_repo_file_ref(state, ref)
    if repo_prefix is not None and repo_relative_path is not None:
        repo = resolve_repo(state.paths, repo_prefix)
        repo_root = resolve_repo_root(state.paths, repo.name)
        candidate = (repo_root / repo_relative_path).resolve()
        try:
            relative_to_repo = candidate.relative_to(repo_root)
        except ValueError as exc:
            raise LaunchError(f"Invalid project repo file ref: {ref}") from exc
        if not candidate.exists() or not candidate.is_file():
            raise LaunchError(f"Project file source does not exist: {ref}")
        return (
            candidate,
            f"{repo.slug}:{relative_to_repo}",
            {
                "path": str(candidate),
                "repo": repo.name,
                "repo_kind": repo.kind,
                "repo_path": repo.path,
                "repo_relative_path": str(relative_to_repo),
            },
        )
    candidate = Path(ref).expanduser()
    if not candidate.is_absolute():
        candidate = state.paths.workspace_root / candidate
    candidate = candidate.resolve()
    if not candidate.exists() or not candidate.is_file():
        raise LaunchError(f"Project file source does not exist: {ref}")
    return (
        candidate,
        str(candidate.relative_to(state.paths.workspace_root)),
        {"path": str(candidate)},
    )


def _resolve_external_artifact_file(state: ProjectState, ref: str) -> Path:
    workspace_root = state.paths.workspace_root.resolve()
    candidate = (workspace_root / ref).resolve()
    try:
        candidate.relative_to(workspace_root)
    except ValueError as exc:
        raise LaunchError(f"Invalid artifact ref: {ref}") from exc
    if candidate.exists() and candidate.is_file():
        return candidate
    if "/" not in ref and "\\" not in ref:
        matches = [
            path
            for path in workspace_root.rglob(ref)
            if path.is_file() and path.resolve().is_relative_to(workspace_root)
        ]
        if len(matches) == 1:
            return matches[0].resolve()
        if len(matches) > 1:
            raise LaunchError(
                f"Artifact ref is ambiguous: {ref}. Use a workspace-relative path."
            )
    raise LaunchError(f"Artifact does not exist: {ref}")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LaunchError(f"Failed to read {path}: {exc}") from exc


def repo_refs_for_sources(sources: tuple[ContextSource, ...]) -> tuple[str, ...]:
    refs: list[str] = []
    for source in sources:
        metadata = source.metadata or {}
        repo = metadata.get("repo")
        if isinstance(repo, str) and repo not in refs:
            refs.append(repo)
    return tuple(refs)


def _split_repo_file_ref(
    state: ProjectState, ref: str
) -> tuple[str | None, str | None]:
    if ":" not in ref:
        return None, None
    prefix, relative_ref = ref.split(":", 1)
    if not relative_ref:
        return None, None
    normalized_prefix = prefix.strip()
    for repo in state.repos:
        if normalized_prefix in {repo.name, repo.slug}:
            return repo.name, relative_ref.lstrip("/")
    return None, None


def _apply_source_budget(
    sources: tuple[ContextSource, ...],
    budget: ProjectSourceBudget,
) -> tuple[ContextSource, ...]:
    if (
        budget.max_source_chars is None
        and budget.max_total_chars is None
        and budget.head_lines is None
        and budget.tail_lines is None
        and budget.line_start is None
        and budget.line_end is None
    ):
        return sources
    remaining_total = budget.max_total_chars
    bounded: list[ContextSource] = []
    for source in sources:
        updated = _apply_source_excerpt(source, budget)
        body = updated.body
        metadata = dict(updated.metadata or {})
        if remaining_total is not None:
            if remaining_total <= 0:
                metadata["original_chars"] = metadata.get("original_chars", len(body))
                metadata["truncated"] = True
                metadata["truncation_notice"] = (
                    "source omitted after total source budget was exhausted"
                )
                body = (
                    "[TRUNCATED: source omitted after total source budget was "
                    "exhausted]\n"
                )
            elif len(body) > remaining_total:
                metadata["original_chars"] = metadata.get("original_chars", len(body))
                body = (
                    body[:remaining_total].rstrip()
                    + "\n[TRUNCATED: source capped by total source budget]"
                )
                metadata["truncated"] = True
                metadata["truncation_notice"] = "source capped by total source budget"
            remaining_total -= len(body)
        bounded.append(replace(updated, body=body, metadata=metadata or None))
    return tuple(bounded)


def _apply_source_excerpt(
    source: ContextSource,
    budget: ProjectSourceBudget,
) -> ContextSource:
    body = source.body
    metadata = dict(source.metadata or {})
    original_body = body
    if source.kind in {"file", "loop_artifact"}:
        body, metadata = _apply_line_excerpt(body, metadata, budget)
    if budget.max_source_chars is not None and len(body) > budget.max_source_chars:
        body = (
            body[: budget.max_source_chars].rstrip()
            + "\n[TRUNCATED: source capped by per-source budget]"
        )
        metadata["truncated"] = True
        metadata["truncation_notice"] = "source capped by per-source budget"
    if body != original_body:
        metadata["original_chars"] = len(original_body)
    return replace(source, body=body, metadata=metadata or None)


def _apply_line_excerpt(
    body: str,
    metadata: dict[str, object],
    budget: ProjectSourceBudget,
) -> tuple[str, dict[str, object]]:
    lines = body.splitlines()
    if not lines:
        return body, metadata
    total_lines = len(lines)
    if budget.line_start is not None or budget.line_end is not None:
        start = budget.line_start or 1
        end = budget.line_end or total_lines
        start = max(start, 1)
        end = min(end, total_lines)
        selected = lines[start - 1 : end]
        if start != 1 or end != total_lines:
            metadata["truncated"] = True
            metadata["selected_lines"] = [start, end]
            metadata["truncation_notice"] = (
                f"showing lines {start}:{end} of {total_lines}"
            )
            return (
                f"[TRUNCATED: showing lines {start}:{end} of {total_lines}]\n"
                + "\n".join(selected),
                metadata,
            )
        return body, metadata
    if budget.head_lines is not None and total_lines > budget.head_lines:
        head = lines[: budget.head_lines]
        if (
            budget.tail_lines is not None
            and total_lines > budget.head_lines + budget.tail_lines
        ):
            tail = lines[-budget.tail_lines :]
            metadata["truncated"] = True
            metadata["selected_lines"] = [
                1,
                budget.head_lines,
                total_lines - budget.tail_lines + 1,
                total_lines,
            ]
            metadata["truncation_notice"] = (
                f"showing first {budget.head_lines} and last "
                f"{budget.tail_lines} lines of {total_lines}"
            )
            return (
                f"[TRUNCATED: showing first {budget.head_lines} and last "
                f"{budget.tail_lines} lines of {total_lines}]\n"
                + "\n".join(head + ["[... truncated middle lines ...]"] + tail),
                metadata,
            )
        metadata["truncated"] = True
        metadata["selected_lines"] = [1, budget.head_lines]
        metadata["truncation_notice"] = (
            f"showing first {budget.head_lines} lines of {total_lines}"
        )
        return (
            f"[TRUNCATED: showing first {budget.head_lines} lines of {total_lines}]\n"
            + "\n".join(head),
            metadata,
        )
    if budget.tail_lines is not None and total_lines > budget.tail_lines:
        tail = lines[-budget.tail_lines :]
        metadata["truncated"] = True
        metadata["selected_lines"] = [total_lines - budget.tail_lines + 1, total_lines]
        metadata["truncation_notice"] = (
            f"showing last {budget.tail_lines} lines of {total_lines}"
        )
        return (
            f"[TRUNCATED: showing last {budget.tail_lines} lines of {total_lines}]\n"
            + "\n".join(tail),
            metadata,
        )
    return body, metadata
