from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from taskledger.models import ContextBundle, ContextSource, ProjectSourceBudget


def build_project_compose_payload(
    *,
    workspace_root: Path,
    bundle: ContextBundle,
    explicit_inputs: Mapping[str, tuple[str, ...]],
    expanded_inputs: Mapping[str, tuple[str, ...]],
    details: Mapping[str, object],
    repo_refs: tuple[str, ...],
    run_in_repo: str | None,
    run_in_repo_source: str | None,
    context_repo_refs: tuple[str, ...],
    execution_cwd: Path | None,
    prompt_path: Path,
    source_budget: ProjectSourceBudget,
    prompt_diagnostics: Mapping[str, object],
    user_prompt: str,
) -> dict[str, object]:
    warnings = list(_compose_warnings(bundle.sources))
    explanations = _compose_explanations(
        explicit_inputs=explicit_inputs,
        expanded_inputs=expanded_inputs,
        expansion_order=cast(list[str], details["expansion_order"]),
        warnings=warnings,
    )
    if prompt_diagnostics.get("exceeds_hard_prompt_limit") is True:
        warnings.append(
            "Composed prompt exceeds the local project safety limit before execution."
        )
    return {
        "kind": "project_compose",
        "project": {
            "context_hash": bundle.content_hash,
            "repo_refs": list(repo_refs),
            "run_in_repo": run_in_repo,
            "run_in_repo_source": run_in_repo_source,
            "context_repo_refs": list(context_repo_refs),
            "execution_cwd": (
                _relative_or_absolute(execution_cwd, workspace_root)
                if execution_cwd is not None
                else None
            ),
            "explicit_inputs": {
                key: list(value) for key, value in explicit_inputs.items()
            },
            "expanded_inputs": {
                key: list(value) for key, value in expanded_inputs.items()
            },
            "source_budget": source_budget.to_dict(),
            "context_inputs": list(expanded_inputs["context_inputs"]),
            "memory_inputs": list(expanded_inputs["memory_inputs"]),
            "file_inputs": list(expanded_inputs["file_inputs"]),
            "item_inputs": list(expanded_inputs["item_inputs"]),
            "inline_inputs": list(expanded_inputs["inline_inputs"]),
            "loop_artifact_inputs": list(expanded_inputs["loop_artifact_inputs"]),
            "source_summary": _compose_source_summary(bundle.sources),
            "expansion_order": list(cast(list[str], details["expansion_order"])),
            "duplicates_removed": list(cast(list[str], details["duplicates_removed"])),
            "warnings": warnings,
            "truncation_notes": warnings,
            "prompt_diagnostics": dict(prompt_diagnostics),
            "prompt_path": str(prompt_path.relative_to(workspace_root)),
            "total_prompt_chars": len(bundle.composed_text),
            "user_prompt": user_prompt,
            "sources": [source.to_dict() for source in bundle.sources],
            "composed_prompt": bundle.composed_text,
            "why": {
                "direct_inputs": _compose_input_counts(explicit_inputs),
                "expanded_inputs": _compose_input_counts(expanded_inputs),
                "expansion_order": list(cast(list[str], details["expansion_order"])),
                "duplicates_removed": list(
                    cast(list[str], details["duplicates_removed"])
                ),
                "run_in_repo": run_in_repo,
                "run_in_repo_source": run_in_repo_source,
                "warning_count": len(warnings),
                "explanations": explanations,
            },
        },
    }


def _compose_source_summary(sources: tuple[ContextSource, ...]) -> dict[str, object]:
    by_kind: dict[str, int] = {}
    by_repo: dict[str, int] = {}
    for source in sources:
        by_kind[source.kind] = by_kind.get(source.kind, 0) + 1
        metadata = source.metadata or {}
        repo = metadata.get("repo")
        if isinstance(repo, str):
            by_repo[repo] = by_repo.get(repo, 0) + 1
    return {
        "total": len(sources),
        "by_kind": by_kind,
        "by_repo": by_repo,
    }


def _compose_warnings(sources: tuple[ContextSource, ...]) -> tuple[str, ...]:
    warnings: list[str] = []
    for source in sources:
        metadata = source.metadata or {}
        truncation_notice = metadata.get("truncation_notice")
        if isinstance(truncation_notice, str):
            warnings.append(f"{source.title or source.ref}: {truncation_notice}")
    return tuple(warnings)


def _compose_input_counts(selection: Mapping[str, tuple[str, ...]]) -> dict[str, int]:
    return {
        "contexts": len(selection["context_inputs"]),
        "memories": len(selection["memory_inputs"]),
        "files": len(selection["file_inputs"]),
        "items": len(selection["item_inputs"]),
        "inline": len(selection["inline_inputs"]),
        "loop_artifacts": len(selection["loop_artifact_inputs"]),
    }


def _compose_explanations(
    *,
    explicit_inputs: Mapping[str, tuple[str, ...]],
    expanded_inputs: Mapping[str, tuple[str, ...]],
    expansion_order: Sequence[str],
    warnings: list[str],
) -> list[str]:
    explanations: list[str] = []
    if expanded_inputs["context_inputs"]:
        explanations.append(
            "saved contexts expanded into "
            f"{len(expanded_inputs['memory_inputs'])} memory refs, "
            f"{len(expanded_inputs['file_inputs'])} file refs, and "
            f"{len(expanded_inputs['item_inputs'])} item refs"
        )
    if expanded_inputs["file_inputs"] != explicit_inputs["file_inputs"]:
        explanations.append(
            "expanded file inputs include files pulled in through "
            "saved contexts or items"
        )
    if len(expansion_order) > sum(
        len(values)
        for values in (
            explicit_inputs["memory_inputs"],
            explicit_inputs["file_inputs"],
            explicit_inputs["item_inputs"],
            explicit_inputs["inline_inputs"],
            explicit_inputs["loop_artifact_inputs"],
        )
    ):
        explanations.append(
            "expansion order shows additional source material "
            "introduced by items or saved contexts before dedupe"
        )
    if warnings:
        explanations.append(
            "truncation warnings explain where source budgets clipped file-like inputs"
        )
    return explanations


def _relative_or_absolute(path: Path, workspace_root: Path) -> str:
    try:
        return str(path.relative_to(workspace_root))
    except ValueError:
        return str(path)
