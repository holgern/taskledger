from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast

from taskledger.errors import LaunchError
from taskledger.models import (
    ARTIFACT_MEMORY_REF_FIELDS,
    DEFAULT_PROJECT_SOURCE_HEAD_LINES,
    DEFAULT_PROJECT_SOURCE_MAX_CHARS,
    DEFAULT_PROJECT_SOURCE_TAIL_LINES,
    DEFAULT_PROJECT_TOTAL_SOURCE_MAX_CHARS,
    FileRenderMode,
    MemoryUpdateMode,
    ProjectArtifactRule,
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
from taskledger.storage.memories import (
    memory_markdown_path as memory_markdown_path,
)
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
from taskledger.storage.stages import (
    append_stage_record as append_stage_record,
)
from taskledger.storage.stages import (
    item_stage_records as item_stage_records,
)
from taskledger.storage.stages import (
    latest_stage_record as latest_stage_record,
)
from taskledger.storage.stages import (
    load_stage_records as load_stage_records,
)
from taskledger.storage.stages import (
    replace_stage_record as replace_stage_record,
)
from taskledger.storage.stages import (
    save_stage_records as save_stage_records,
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
from taskledger.storage.workflows import (
    delete_workflow_definition as delete_workflow_definition,
)
from taskledger.storage.workflows import (
    load_workflow_definitions as load_workflow_definitions,
)
from taskledger.storage.workflows import (
    resolve_workflow_definition as resolve_workflow_definition,
)
from taskledger.storage.workflows import (
    save_workflow_definitions as save_workflow_definitions,
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
# default_file_render_mode = "content"
# default_save_run_reports = true
# default_source_max_chars = {DEFAULT_PROJECT_SOURCE_MAX_CHARS}
# default_total_source_max_chars = {DEFAULT_PROJECT_TOTAL_SOURCE_MAX_CHARS}
# default_source_head_lines = {DEFAULT_PROJECT_SOURCE_HEAD_LINES}
# default_source_tail_lines = {DEFAULT_PROJECT_SOURCE_TAIL_LINES}
# default_context_order = ["memory", "file", "item", "inline", "loop_artifact"]
# workflow_schema = "opsx-lite"
# project_context = "Project-specific workflow guidance."
# default_artifact_order = ["analysis", "plan", "implementation", "validation"]
#
# [artifact_rules.analysis]
# memory_ref_field = "analysis_memory_ref"
#
# [artifact_rules.plan]
# depends_on = ["analysis"]
# memory_ref_field = "plan_memory_ref"
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
    workflows_dir = project_dir / "workflows"
    memories_dir = project_dir / "memories"
    contexts_dir = project_dir / "contexts"
    items_dir = project_dir / "items"
    stages_dir = project_dir / "stages"
    return ProjectPaths(
        workspace_root=workspace_root,
        project_dir=project_dir,
        config_path=project_dir / "project.toml",
        repos_dir=repos_dir,
        repo_index_path=repos_dir / "index.json",
        workflows_dir=workflows_dir,
        workflow_index_path=workflows_dir / "index.json",
        memories_dir=memories_dir,
        contexts_dir=contexts_dir,
        context_index_path=contexts_dir / "index.json",
        items_dir=items_dir,
        stages_dir=stages_dir,
        stage_index_path=stages_dir / "index.json",
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
        paths.workflows_dir,
        paths.memories_dir,
        paths.contexts_dir,
        paths.items_dir,
        paths.stages_dir,
        paths.runs_dir,
        paths.project_dir / "introductions",
        paths.project_dir / "tasks",
        paths.project_dir / "plans",
        paths.project_dir / "questions",
        paths.project_dir / "changes",
        paths.project_dir / "events",
        paths.project_dir / "indexes",
        validation_records_dir(paths),
    ):
        if directory.exists():
            continue
        directory.mkdir(parents=True, exist_ok=True)
        created.append(str(directory))
    for path, contents in (
        (paths.config_path, DEFAULT_PROJECT_TOML),
        (paths.repo_index_path, "[]\n"),
        (paths.workflow_index_path, "[]\n"),
        (paths.context_index_path, "[]\n"),
        (paths.stage_index_path, "[]\n"),
        (paths.project_dir / "indexes" / "tasks.json", "[]\n"),
        (paths.project_dir / "indexes" / "active_locks.json", "[]\n"),
        (paths.project_dir / "indexes" / "dependencies.json", "[]\n"),
        (paths.project_dir / "indexes" / "introductions.json", "[]\n"),
        (validation_records_index_path(paths), "[]\n"),
    ):
        if path.exists():
            continue
        _write_text(path, contents)
        created.append(str(path))
    return paths, created


def ensure_project_exists(workspace_root: Path) -> ProjectPaths:
    paths = resolve_project_paths(workspace_root)
    _reject_legacy_item_memory_indexes(paths)
    missing = [
        path
        for path in (
            paths.config_path,
            paths.repo_index_path,
            paths.workflow_index_path,
            paths.context_index_path,
            paths.stage_index_path,
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
    default_file_render_mode = overrides.get(
        "default_file_render_mode",
        base.default_file_render_mode,
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
    workflow_schema = overrides.get("workflow_schema", base.workflow_schema)
    project_context = overrides.get("project_context", base.project_context)
    artifact_rules = _artifact_rules_from_overrides(
        overrides.get("artifact_rules"),
        base.artifact_rules,
    )
    default_artifact_order = overrides.get(
        "default_artifact_order",
        list(base.default_artifact_order),
    )
    if not isinstance(default_memory_update_mode, str):
        raise LaunchError("Project config default_memory_update_mode must be a string.")
    if default_memory_update_mode not in {"replace", "append", "prepend"}:
        raise LaunchError(
            "Project config default_memory_update_mode must be "
            "replace, append, or prepend."
        )
    if not isinstance(default_file_render_mode, str):
        raise LaunchError("Project config default_file_render_mode must be a string.")
    if default_file_render_mode not in {"content", "reference"}:
        raise LaunchError(
            "Project config default_file_render_mode must be content or reference."
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
    if workflow_schema is not None and not isinstance(workflow_schema, str):
        raise LaunchError("Project config workflow_schema must be a string.")
    if project_context is not None and not isinstance(project_context, str):
        raise LaunchError("Project config project_context must be a string.")
    if not isinstance(default_artifact_order, list) or not all(
        isinstance(item, str) for item in default_artifact_order
    ):
        raise LaunchError(
            "Project config default_artifact_order must be a list of strings."
        )
    _validate_artifact_order_and_dependencies(
        artifact_rules,
        default_artifact_order=tuple(default_artifact_order),
    )
    return ProjectConfig(
        default_memory_update_mode=cast(
            MemoryUpdateMode,
            default_memory_update_mode,
        ),
        default_file_render_mode=cast(FileRenderMode, default_file_render_mode),
        default_save_run_reports=default_save_run_reports,
        default_source_max_chars=cast(int | None, default_source_max_chars),
        default_total_source_max_chars=cast(int | None, default_total_source_max_chars),
        default_source_head_lines=cast(int | None, default_source_head_lines),
        default_source_tail_lines=cast(int | None, default_source_tail_lines),
        default_context_order=tuple(default_context_order),
        workflow_schema=cast(str | None, workflow_schema),
        project_context=cast(str | None, project_context),
        artifact_rules=artifact_rules,
        default_artifact_order=tuple(default_artifact_order),
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
            "default_file_render_mode",
            "default_save_run_reports",
            "default_source_max_chars",
            "default_total_source_max_chars",
            "default_source_head_lines",
            "default_source_tail_lines",
            "default_context_order",
            "workflow_schema",
            "project_context",
            "artifact_rules",
            "default_artifact_order",
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
    file_render_mode = data.get("default_file_render_mode")
    if file_render_mode is not None and (
        not isinstance(file_render_mode, str)
        or file_render_mode not in {"content", "reference"}
    ):
        raise LaunchError(
            "Project config key 'default_file_render_mode' must be "
            f"content or reference in {path}"
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
    workflow_schema = data.get("workflow_schema")
    if workflow_schema is not None and not isinstance(workflow_schema, str):
        raise LaunchError(
            f"Project config key 'workflow_schema' must be a string in {path}"
        )
    project_context = data.get("project_context")
    if project_context is not None and not isinstance(project_context, str):
        raise LaunchError(
            f"Project config key 'project_context' must be a string in {path}"
        )
    default_artifact_order = data.get("default_artifact_order")
    if default_artifact_order is not None and (
        not isinstance(default_artifact_order, list)
        or not all(isinstance(item, str) for item in default_artifact_order)
    ):
        raise LaunchError(
            "Project config key 'default_artifact_order' must be "
            f"a list of strings in {path}"
        )
    artifact_rules = data.get("artifact_rules")
    if artifact_rules is not None:
        if not isinstance(artifact_rules, dict):
            raise LaunchError(
                f"Project config key 'artifact_rules' must be a table in {path}"
            )
        parsed_rules = _artifact_rules_from_mapping(artifact_rules, path=path)
        _validate_artifact_order_and_dependencies(
            parsed_rules,
            default_artifact_order=tuple(default_artifact_order or ()),
            path=path,
        )


def _ensure_additive_project_files(paths: ProjectPaths) -> None:
    for directory in (
        paths.repos_dir,
        paths.memories_dir,
        paths.items_dir,
        paths.runs_dir,
        paths.project_dir / "introductions",
        paths.project_dir / "tasks",
        paths.project_dir / "plans",
        paths.project_dir / "questions",
        paths.project_dir / "changes",
        paths.project_dir / "events",
        paths.project_dir / "indexes",
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
        paths.project_dir / "indexes" / "tasks.json",
        paths.project_dir / "indexes" / "active_locks.json",
        paths.project_dir / "indexes" / "dependencies.json",
        paths.project_dir / "indexes" / "introductions.json",
        validation_records_index_path(paths),
    ):
        if path.exists():
            continue
        _write_text(path, "[]\n")


def _reject_legacy_item_memory_indexes(paths: ProjectPaths) -> None:
    legacy_item_index = paths.items_dir / "index.json"
    legacy_memory_index = paths.memories_dir / "index.json"
    if legacy_item_index.exists():
        raise LaunchError(
            "Legacy item JSON storage is unsupported after this refactor: "
            f"remove {legacy_item_index}."
        )
    if legacy_memory_index.exists():
        raise LaunchError(
            "Legacy memory JSON storage is unsupported after this refactor: "
            f"remove {legacy_memory_index}."
        )


def _artifact_rules_from_overrides(
    raw_rules: object,
    base_rules: tuple[ProjectArtifactRule, ...],
) -> tuple[ProjectArtifactRule, ...]:
    if raw_rules is None:
        return base_rules
    if not isinstance(raw_rules, dict):
        raise LaunchError("Project config artifact_rules must be a table.")
    return _artifact_rules_from_mapping(raw_rules)


def _artifact_rules_from_mapping(
    raw_rules: dict[str, object],
    *,
    path: Path | None = None,
) -> tuple[ProjectArtifactRule, ...]:
    rules: list[ProjectArtifactRule] = []
    for name, value in raw_rules.items():
        if not isinstance(value, dict):
            raise LaunchError(_artifact_rule_error(name, "must be a table", path=path))
        for key in value:
            if key not in {"depends_on", "memory_ref_field", "label", "description"}:
                raise LaunchError(
                    _artifact_rule_error(
                        name,
                        f"has unsupported key '{key}'",
                        path=path,
                    )
                )
        depends_on = value.get("depends_on", [])
        if not isinstance(depends_on, list) or not all(
            isinstance(item, str) for item in depends_on
        ):
            raise LaunchError(
                _artifact_rule_error(
                    name,
                    "depends_on must be a list of strings",
                    path=path,
                )
            )
        memory_ref_field = value.get("memory_ref_field")
        if memory_ref_field is not None and (
            not isinstance(memory_ref_field, str)
            or memory_ref_field not in ARTIFACT_MEMORY_REF_FIELDS
        ):
            allowed = ", ".join(ARTIFACT_MEMORY_REF_FIELDS)
            raise LaunchError(
                _artifact_rule_error(
                    name,
                    f"memory_ref_field must be one of: {allowed}",
                    path=path,
                )
            )
        label = value.get("label")
        if label is not None and not isinstance(label, str):
            raise LaunchError(
                _artifact_rule_error(name, "label must be a string", path=path)
            )
        description = value.get("description")
        if description is not None and not isinstance(description, str):
            raise LaunchError(
                _artifact_rule_error(name, "description must be a string", path=path)
            )
        rules.append(
            ProjectArtifactRule(
                name=name,
                depends_on=tuple(depends_on),
                memory_ref_field=cast(str | None, memory_ref_field),
                label=cast(str | None, label),
                description=cast(str | None, description),
            )
        )
    return tuple(rules)


def _validate_artifact_order_and_dependencies(
    artifact_rules: tuple[ProjectArtifactRule, ...],
    *,
    default_artifact_order: tuple[str, ...],
    path: Path | None = None,
) -> None:
    if not artifact_rules:
        return
    names = {rule.name for rule in artifact_rules}
    if len(names) != len(artifact_rules):
        raise LaunchError(
            _project_config_error("Artifact rule names must be unique.", path)
        )
    for rule in artifact_rules:
        for dependency in rule.depends_on:
            if dependency not in names:
                raise LaunchError(
                    _project_config_error(
                        "Artifact rule "
                        f"'{rule.name}' depends on unknown artifact "
                        f"'{dependency}'.",
                        path,
                    )
                )
    if default_artifact_order:
        unknown = [name for name in default_artifact_order if name not in names]
        if unknown:
            raise LaunchError(
                _project_config_error(
                    "default_artifact_order references unknown artifacts: "
                    + ", ".join(sorted(unknown)),
                    path,
                )
            )
    visiting: set[str] = set()
    visited: set[str] = set()
    graph = {rule.name: rule.depends_on for rule in artifact_rules}

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise LaunchError(
                _project_config_error(
                    f"Artifact dependency cycle detected at '{name}'.",
                    path,
                )
            )
        visiting.add(name)
        for dependency in graph[name]:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        visit(name)


def _artifact_rule_error(name: str, message: str, *, path: Path | None) -> str:
    return _project_config_error(f"Artifact rule '{name}' {message}.", path)


def _project_config_error(message: str, path: Path | None) -> str:
    if path is None:
        return message
    return f"{message} in {path}"
