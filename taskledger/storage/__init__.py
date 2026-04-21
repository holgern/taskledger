from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast

from taskledger.errors import LaunchError
from taskledger.models import (
    DEFAULT_PROJECT_SOURCE_HEAD_LINES,
    DEFAULT_PROJECT_SOURCE_MAX_CHARS,
    DEFAULT_PROJECT_SOURCE_TAIL_LINES,
    DEFAULT_PROJECT_TOTAL_SOURCE_MAX_CHARS,
    MemoryUpdateMode,
    ProjectConfig,
    ProjectMemory,
    ProjectPaths,
    ProjectRunRecord,
    ProjectState,
)
from taskledger.storage.common import load_json_object as _load_json_object
from taskledger.storage.common import read_text as _read_text
from taskledger.storage.common import write_text as _write_text
from taskledger.storage.contexts import delete_context as delete_context
from taskledger.storage.contexts import load_contexts as load_contexts
from taskledger.storage.contexts import rename_context as rename_context
from taskledger.storage.contexts import resolve_context as resolve_context
from taskledger.storage.contexts import save_context as save_context
from taskledger.storage.contexts import (
    save_context_entry as save_context_entry,
)
from taskledger.storage.contexts import save_contexts as save_contexts
from taskledger.storage.items import create_work_item as create_work_item
from taskledger.storage.items import load_work_items as load_work_items
from taskledger.storage.items import resolve_work_item as resolve_work_item
from taskledger.storage.items import save_work_item as save_work_item
from taskledger.storage.items import save_work_items as save_work_items
from taskledger.storage.items import update_work_item as update_work_item
from taskledger.storage.memories import create_memory as create_memory
from taskledger.storage.memories import delete_memory as delete_memory
from taskledger.storage.memories import load_memories as load_memories
from taskledger.storage.memories import memory_body_path as memory_body_path
from taskledger.storage.memories import read_memory_body as read_memory_body
from taskledger.storage.memories import refresh_memory as refresh_memory
from taskledger.storage.memories import rename_memory as rename_memory
from taskledger.storage.memories import resolve_memory as resolve_memory
from taskledger.storage.memories import save_memories as save_memories
from taskledger.storage.memories import (
    update_memory_body as update_memory_body,
)
from taskledger.storage.memories import (
    update_memory_tags as update_memory_tags,
)
from taskledger.storage.memories import write_memory_body as write_memory_body
from taskledger.storage.repos import (
    add_repo as add_repo,
)
from taskledger.storage.repos import (
    clear_default_execution_repo as clear_default_execution_repo,
)
from taskledger.storage.repos import (
    load_repos as load_repos,
)
from taskledger.storage.repos import (
    remove_repo as remove_repo,
)
from taskledger.storage.repos import (
    resolve_repo as resolve_repo,
)
from taskledger.storage.repos import (
    resolve_repo_root as resolve_repo_root,
)
from taskledger.storage.repos import (
    save_repos as save_repos,
)
from taskledger.storage.repos import (
    set_default_execution_repo as set_default_execution_repo,
)
from taskledger.storage.repos import (
    set_repo_role as set_repo_role,
)
from taskledger.storage.runs import (
    cleanup_runs as cleanup_runs,
)
from taskledger.storage.runs import (
    create_run_dir as create_run_dir,
)
from taskledger.storage.runs import (
    delete_run as delete_run,
)
from taskledger.storage.runs import (
    load_run_records as load_run_records,
)
from taskledger.storage.runs import (
    resolve_run_record as resolve_run_record,
)
from taskledger.storage.runs import (
    save_run_record as save_run_record,
)
from taskledger.storage.validation import (
    append_validation_record as append_validation_record,
)
from taskledger.storage.validation import (
    load_validation_records as load_validation_records,
)
from taskledger.storage.validation import (
    remove_validation_records as remove_validation_records,
)
from taskledger.storage.validation import (
    save_validation_records as save_validation_records,
)
from taskledger.storage.validation import (
    validation_records_dir as validation_records_dir,
)
from taskledger.storage.validation import (
    validation_records_index_path as validation_records_index_path,
)

try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    tomllib = importlib.import_module("tomli")

DEFAULT_PROJECT_TOML = f"""# Project-local taskledger overrides.
# The source-budget settings below are the active composition defaults.
# Lower them for stricter prompts, or raise them when a run needs more context.
# Use your runtime preview command to inspect prompt size first.
# Supported keys:
# default_memory_update_mode = "replace"
# default_save_run_reports = true
# default_source_max_chars = {DEFAULT_PROJECT_SOURCE_MAX_CHARS}
# default_total_source_max_chars = {DEFAULT_PROJECT_TOTAL_SOURCE_MAX_CHARS}
# default_source_head_lines = {DEFAULT_PROJECT_SOURCE_HEAD_LINES}
# default_source_tail_lines = {DEFAULT_PROJECT_SOURCE_TAIL_LINES}
# default_context_order = ["memory", "file", "item", "inline", "loop_artifact"]
"""


def resolve_taskledger_root(workspace_root: Path) -> Path:
    return workspace_root / ".taskledger"


def resolve_project_paths(workspace_root: Path) -> ProjectPaths:
    return _project_paths_for_root(
        workspace_root,
        resolve_taskledger_root(workspace_root),
    )


def _project_paths_for_root(workspace_root: Path, project_dir: Path) -> ProjectPaths:
    repos_dir = project_dir / "repos"
    memories_dir = project_dir / "memories"
    contexts_dir = project_dir / "contexts"
    items_dir = project_dir / "items"
    return ProjectPaths(
        workspace_root=workspace_root,
        project_dir=project_dir,
        config_path=project_dir / "project.toml",
        repos_dir=repos_dir,
        repo_index_path=repos_dir / "index.json",
        memories_dir=memories_dir,
        memory_index_path=memories_dir / "index.json",
        contexts_dir=contexts_dir,
        context_index_path=contexts_dir / "index.json",
        items_dir=items_dir,
        item_index_path=items_dir / "index.json",
        runs_dir=project_dir / "runs",
    )


def init_project_state(workspace_root: Path) -> tuple[ProjectPaths, list[str]]:
    paths = _project_paths_for_root(
        workspace_root,
        resolve_taskledger_root(workspace_root),
    )
    created: list[str] = []
    for directory in (
        paths.project_dir,
        paths.repos_dir,
        paths.memories_dir,
        paths.contexts_dir,
        paths.items_dir,
        paths.runs_dir,
        validation_records_dir(paths),
    ):
        if directory.exists():
            continue
        directory.mkdir(parents=True, exist_ok=True)
        created.append(str(directory))
    for path, contents in (
        (paths.config_path, DEFAULT_PROJECT_TOML),
        (paths.repo_index_path, "[]\n"),
        (paths.memory_index_path, "[]\n"),
        (paths.context_index_path, "[]\n"),
        (paths.item_index_path, "[]\n"),
        (validation_records_index_path(paths), "[]\n"),
    ):
        if path.exists():
            continue
        _write_text(path, contents)
        created.append(str(path))
    return paths, created


def ensure_project_exists(workspace_root: Path) -> ProjectPaths:
    paths = resolve_project_paths(workspace_root)
    missing = [
        path
        for path in (
            paths.config_path,
            paths.repo_index_path,
            paths.memory_index_path,
            paths.context_index_path,
            paths.item_index_path,
        )
        if not path.exists()
    ]
    if missing:
        raise LaunchError(
            "Project state is not initialized. Run 'taskledger init' first."
        )
    _ensure_additive_project_files(paths)
    return paths


def load_project_state(
    workspace_root: Path, *, recent_runs_limit: int | None = 5
) -> ProjectState:
    paths = ensure_project_exists(workspace_root)
    return ProjectState(
        paths=paths,
        config_overrides=load_project_config_overrides(paths),
        repos=tuple(load_repos(paths)),
        memories=tuple(load_memories(paths)),
        contexts=tuple(load_contexts(paths)),
        work_items=tuple(load_work_items(paths)),
        recent_runs=tuple(load_run_records(paths, limit=recent_runs_limit)),
    )


def load_project_config_overrides(paths: ProjectPaths) -> dict[str, object]:
    text = _read_text(paths.config_path).strip()
    if not text:
        return {}
    try:
        data = tomllib.loads(text)
    except Exception as exc:  # pragma: no cover - tomllib type varies by runtime
        raise LaunchError(f"Invalid project config {paths.config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LaunchError(
            f"Invalid project config {paths.config_path}: expected a TOML table."
        )
    _validate_project_config_overrides(data, paths.config_path)
    return data


def merge_project_config(
    base: ProjectConfig, overrides: dict[str, object]
) -> ProjectConfig:
    default_memory_update_mode = overrides.get(
        "default_memory_update_mode", base.default_memory_update_mode
    )
    default_save_run_reports = overrides.get(
        "default_save_run_reports", base.default_save_run_reports
    )
    default_source_max_chars = overrides.get(
        "default_source_max_chars", base.default_source_max_chars
    )
    default_total_source_max_chars = overrides.get(
        "default_total_source_max_chars", base.default_total_source_max_chars
    )
    default_source_head_lines = overrides.get(
        "default_source_head_lines", base.default_source_head_lines
    )
    default_source_tail_lines = overrides.get(
        "default_source_tail_lines", base.default_source_tail_lines
    )
    default_context_order = overrides.get(
        "default_context_order", list(base.default_context_order)
    )
    if not isinstance(default_memory_update_mode, str):
        raise LaunchError("Project config default_memory_update_mode must be a string.")
    if default_memory_update_mode not in {"replace", "append", "prepend"}:
        raise LaunchError(
            "Project config default_memory_update_mode must be "
            "replace, append, or prepend."
        )
    if not isinstance(default_save_run_reports, bool):
        raise LaunchError("Project config default_save_run_reports must be a boolean.")
    for value, label in (
        (default_source_max_chars, "default_source_max_chars"),
        (default_total_source_max_chars, "default_total_source_max_chars"),
        (default_source_head_lines, "default_source_head_lines"),
        (default_source_tail_lines, "default_source_tail_lines"),
    ):
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise LaunchError(f"Project config {label} must be a positive integer.")
    if not isinstance(default_context_order, list) or not all(
        isinstance(item, str) for item in default_context_order
    ):
        raise LaunchError(
            "Project config default_context_order must be a list of strings."
        )
    return ProjectConfig(
        default_memory_update_mode=cast(
            MemoryUpdateMode,
            default_memory_update_mode,
        ),
        default_save_run_reports=default_save_run_reports,
        default_source_max_chars=cast(int | None, default_source_max_chars),
        default_total_source_max_chars=cast(int | None, default_total_source_max_chars),
        default_source_head_lines=cast(int | None, default_source_head_lines),
        default_source_tail_lines=cast(int | None, default_source_tail_lines),
        default_context_order=tuple(default_context_order),
    )


def promote_run_to_memory(
    paths: ProjectPaths, run_id: str, *, name: str
) -> tuple[ProjectRunRecord, ProjectMemory]:
    record = resolve_run_record(paths, run_id)
    payload = _load_json_object(
        paths.workspace_root / record.result_path,
        "project run result",
    )
    final_message = payload.get("final_message")
    stdout = payload.get("stdout")
    body = final_message if isinstance(final_message, str) else stdout
    if not isinstance(body, str) or not body.strip():
        raise LaunchError(f"Project run {run_id} has no text output to promote.")
    memory = create_memory(paths, name=name, body=body, source_run_id=run_id)
    return record, memory


def promote_run_report_to_memory(
    paths: ProjectPaths, run_id: str, *, name: str
) -> tuple[ProjectRunRecord, ProjectMemory]:
    record = resolve_run_record(paths, run_id)
    if not record.report_path:
        raise LaunchError(f"Project run {run_id} has no saved report to promote.")
    report_path = paths.workspace_root / record.report_path
    body = _read_text(report_path)
    if not body.strip():
        raise LaunchError(f"Project run {run_id} report is empty.")
    memory = create_memory(paths, name=name, body=body, source_run_id=run_id)
    return record, memory


def _validate_project_config_overrides(data: dict[str, object], path: Path) -> None:
    for key in data:
        if key not in {
            "default_memory_update_mode",
            "default_save_run_reports",
            "default_source_max_chars",
            "default_total_source_max_chars",
            "default_source_head_lines",
            "default_source_tail_lines",
            "default_context_order",
        }:
            raise LaunchError(f"Unsupported project config key '{key}' in {path}")
    mode = data.get("default_memory_update_mode")
    if mode is not None and (
        not isinstance(mode, str) or mode not in {"replace", "append", "prepend"}
    ):
        raise LaunchError(
            "Project config key 'default_memory_update_mode' must be "
            f"replace, append, or prepend in {path}"
        )
    save_reports = data.get("default_save_run_reports")
    if save_reports is not None and not isinstance(save_reports, bool):
        raise LaunchError(
            f"Project config key 'default_save_run_reports' must be a boolean in {path}"
        )
    for key in (
        "default_source_max_chars",
        "default_total_source_max_chars",
        "default_source_head_lines",
        "default_source_tail_lines",
    ):
        value = data.get(key)
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise LaunchError(
                f"Project config key '{key}' must be a positive integer in {path}"
            )
    context_order = data.get("default_context_order")
    if context_order is not None:
        if not isinstance(context_order, list) or not all(
            isinstance(item, str) for item in context_order
        ):
            raise LaunchError(
                "Project config key 'default_context_order' must be "
                f"a list of strings in {path}"
            )


def _ensure_additive_project_files(paths: ProjectPaths) -> None:
    for directory in (
        paths.repos_dir,
        paths.items_dir,
        paths.runs_dir,
        validation_records_dir(paths),
    ):
        if directory.exists():
            continue
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LaunchError(f"Failed to create {directory}: {exc}") from exc
    for path in (
        paths.repo_index_path,
        paths.item_index_path,
        validation_records_index_path(paths),
    ):
        if path.exists():
            continue
        _write_text(path, "[]\n")
