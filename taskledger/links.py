from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectState


def task_has_project_links(task: object) -> bool:
    return bool(
        getattr(task, "project_item_ref", None)
        or getattr(task, "project_memory_refs", None)
        or getattr(task, "project_context_refs", None)
        or getattr(task, "project_save_target_ref", None)
    )


def broken_context_refs(
    state: ProjectState,
    *,
    memory_ids: set[str],
    item_ids: set[str],
) -> list[str]:
    broken: list[str] = []
    for entry in state.contexts:
        missing_context_memories = [
            ref for ref in entry.memory_refs if ref not in memory_ids
        ]
        missing_context_items = [ref for ref in entry.item_refs if ref not in item_ids]
        missing_loop_artifacts = [
            ref
            for ref in entry.loop_latest_refs
            if not _external_artifact_exists(state.paths.workspace_root, ref)
        ]
        details: list[str] = []
        if missing_context_memories:
            details.append("memories=" + ",".join(missing_context_memories))
        if missing_context_items:
            details.append("items=" + ",".join(missing_context_items))
        if missing_loop_artifacts:
            details.append("artifacts=" + ",".join(missing_loop_artifacts))
        if details:
            broken.append(f"{entry.slug}: {'; '.join(details)}")
    return broken


def broken_item_links(
    state: ProjectState,
    *,
    memory_ids: set[str],
    run_ids: set[str],
    loop_ids: set[str],
) -> list[str]:
    broken: list[str] = []
    item_ids = {item.id for item in state.work_items}
    for item in state.work_items:
        missing_item_memories = [
            ref
            for ref in (
                item.analysis_memory_ref,
                item.state_memory_ref,
                item.plan_memory_ref,
                item.implementation_memory_ref,
                item.validation_memory_ref,
            )
            if ref is not None and ref not in memory_ids
        ]
        missing_linked_memories = [
            ref for ref in item.linked_memories if ref not in memory_ids
        ]
        missing_linked_runs = [ref for ref in item.linked_runs if ref not in run_ids]
        missing_linked_loops = [
            ref for ref in item.linked_loop_tasks if ref not in loop_ids
        ]
        missing_dependencies = [ref for ref in item.depends_on if ref not in item_ids]
        details: list[str] = []
        if missing_item_memories:
            details.append("memories=" + ",".join(missing_item_memories))
        if missing_linked_memories:
            details.append("linked_memories=" + ",".join(missing_linked_memories))
        if missing_linked_runs:
            details.append("linked_runs=" + ",".join(missing_linked_runs))
        if missing_linked_loops:
            details.append("linked_loops=" + ",".join(missing_linked_loops))
        if missing_dependencies:
            details.append("depends_on=" + ",".join(missing_dependencies))
        if item.save_target_ref is not None and item.save_target_ref not in memory_ids:
            details.append("save_target=" + item.save_target_ref)
        if details:
            broken.append(f"{item.id}: {'; '.join(details)}")
    return broken


def repo_path_missing(root: Path) -> bool:
    return not root.exists()


def _external_artifact_exists(workspace_root: Path, ref: str) -> bool:
    try:
        candidate = (workspace_root.resolve() / ref).resolve()
        candidate.relative_to(workspace_root.resolve())
    except ValueError:
        return False
    return candidate.exists()
