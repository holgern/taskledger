from __future__ import annotations

from pathlib import Path

from taskledger.links import broken_context_refs as _broken_context_refs
from taskledger.links import broken_item_links as _broken_item_links
from taskledger.models import ProjectState
from taskledger.storage import (
    ensure_project_exists,
    load_project_state,
    memory_body_path,
    resolve_project_paths,
    validation_records_index_path,
)
from taskledger.workflow import build_workflow_summary

_EXPECTED_PATHS = (
    "project_dir",
    "config_path",
    "repos_dir",
    "repo_index_path",
    "workflows_dir",
    "workflow_index_path",
    "memories_dir",
    "memory_index_path",
    "contexts_dir",
    "context_index_path",
    "items_dir",
    "item_index_path",
    "stages_dir",
    "stage_index_path",
    "runs_dir",
)


def inspect_project(workspace_root: Path) -> dict[str, object]:
    paths = resolve_project_paths(workspace_root)
    expected_paths = [
        getattr(paths, name) for name in _EXPECTED_PATHS if hasattr(paths, name)
    ]
    expected_paths.append(validation_records_index_path(paths))
    missing_paths = tuple(str(path) for path in expected_paths if not path.exists())
    if missing_paths:
        return {
            "project_dir": str(paths.project_dir),
            "initialized": False,
            "healthy": False,
            "counts": {
                "repos": 0,
                "memories": 0,
                "contexts": 0,
                "work_items": 0,
                "runs": 0,
            },
            "errors": ["Project state is not initialized."],
            "warnings": [],
            "missing_paths": list(missing_paths),
            "missing_repo_roots": [],
            "missing_memory_files": [],
            "empty_memories": [],
            "broken_context_refs": [],
            "broken_item_links": [],
            "orphan_run_dirs": [],
            "workflow": None,
        }
    try:
        ensure_project_exists(workspace_root)
        state = load_project_state(workspace_root, recent_runs_limit=None)
    except Exception as exc:
        return {
            "project_dir": str(paths.project_dir),
            "initialized": True,
            "healthy": False,
            "counts": {
                "repos": 0,
                "memories": 0,
                "contexts": 0,
                "work_items": 0,
                "runs": 0,
            },
            "errors": [str(exc)],
            "warnings": [],
            "missing_paths": [],
            "missing_repo_roots": [],
            "missing_memory_files": [],
            "empty_memories": [],
            "broken_context_refs": [],
            "broken_item_links": [],
            "orphan_run_dirs": [],
            "workflow": None,
        }
    return _report_for_state(state)


def _report_for_state(state: ProjectState) -> dict[str, object]:
    memory_ids = {item.id for item in state.memories}
    item_ids = {item.id for item in state.work_items}
    run_ids = {item.run_id for item in state.recent_runs}
    loop_ids = {ref for item in state.work_items for ref in item.linked_loop_tasks}
    missing_repo_roots = [
        repo.slug for repo in state.repos if not Path(repo.path).is_dir()
    ]
    missing_memory_files, empty_memories = _memory_issues(state)
    broken_context_refs = _broken_context_refs(
        state,
        memory_ids=memory_ids,
        item_ids=item_ids,
    )
    broken_item_links = _broken_item_links(
        state,
        memory_ids=memory_ids,
        run_ids=run_ids,
        loop_ids=loop_ids,
    )
    orphan_run_dirs = sorted(
        entry.name
        for entry in state.paths.runs_dir.iterdir()
        if entry.is_dir() and not (entry / "record.json").exists()
    )
    workflow = build_workflow_summary(state)
    errors = []
    warnings = []
    if missing_repo_roots:
        errors.append("Tracked repos are missing on disk.")
    if missing_memory_files:
        errors.append("Memory index entries point to missing body files.")
    if broken_context_refs:
        errors.append("Saved contexts reference missing project artifacts.")
    if broken_item_links:
        errors.append("Work items contain broken links.")
    if orphan_run_dirs:
        warnings.append("Run directories exist without record.json files.")
    if empty_memories:
        warnings.append("Some memories are empty.")
    if workflow is not None:
        counts = workflow.get("counts", {})
        if isinstance(counts, dict) and counts.get("blocked"):
            warnings.append("Workflow dependencies block some items.")
    return {
        "project_dir": str(state.paths.project_dir),
        "initialized": True,
        "healthy": not errors,
        "counts": {
            "repos": len(state.repos),
            "memories": len(state.memories),
            "contexts": len(state.contexts),
            "work_items": len(state.work_items),
            "runs": len(state.recent_runs),
        },
        "errors": errors,
        "warnings": warnings,
        "missing_paths": [],
        "missing_repo_roots": missing_repo_roots,
        "missing_memory_files": missing_memory_files,
        "empty_memories": empty_memories,
        "broken_context_refs": broken_context_refs,
        "broken_item_links": broken_item_links,
        "orphan_run_dirs": orphan_run_dirs,
        "workflow": workflow,
    }


def _memory_issues(state: ProjectState) -> tuple[list[str], list[str]]:
    missing_memory_files: list[str] = []
    empty_memories: list[str] = []
    for memory in state.memories:
        body_path = memory_body_path(state.paths, memory)
        if not body_path.exists():
            if memory.summary is not None or memory.content_hash is not None:
                missing_memory_files.append(memory.id)
            continue
        if not body_path.read_text(encoding="utf-8").strip():
            empty_memories.append(memory.id)
    return missing_memory_files, empty_memories
