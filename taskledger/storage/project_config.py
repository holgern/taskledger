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
    ProjectPaths,
)
from taskledger.storage.common import read_text

try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    tomllib = importlib.import_module("tomli")

LOCATION_CONFIG_KEYS = frozenset({"config_version", "taskledger_dir"})
WORKFLOW_CONFIG_KEYS = frozenset(
    {
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
    }
)
SUPPORTED_PROJECT_CONFIG_KEYS = LOCATION_CONFIG_KEYS | WORKFLOW_CONFIG_KEYS


def render_default_taskledger_toml(taskledger_dir: str = ".taskledger") -> str:
    return f"""# Project-local taskledger configuration.
# This file lives in the source project root.
config_version = 1
taskledger_dir = {taskledger_dir!r}

# Project-local taskledger overrides.
# The source-budget settings below are the active composition defaults.
# Lower them for stricter prompts, or raise them when a run needs more context.
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
"""


DEFAULT_TASKLEDGER_TOML = render_default_taskledger_toml()
DEFAULT_PROJECT_TOML = DEFAULT_TASKLEDGER_TOML


def load_project_config_overrides(paths: ProjectPaths) -> dict[str, object]:
    data = load_project_config_document(paths.config_path)
    return {key: value for key, value in data.items() if key in WORKFLOW_CONFIG_KEYS}


def load_project_config_document(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    text = read_text(path).strip()
    if not text:
        return {}
    try:
        data = tomllib.loads(text)
    except Exception as exc:  # pragma: no cover - tomllib type varies by runtime
        raise LaunchError(f"Invalid project config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LaunchError(f"Invalid project config {path}: expected a TOML table.")
    _validate_project_config_overrides(data, path)
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
        workflow_schema=workflow_schema,
        project_context=project_context,
        artifact_rules=artifact_rules,
        default_artifact_order=tuple(default_artifact_order),
    )


def _validate_project_config_overrides(data: dict[str, object], path: Path) -> None:
    for key in data:
        if key not in SUPPORTED_PROJECT_CONFIG_KEYS:
            raise LaunchError(f"Unsupported project config key '{key}' in {path}")
    config_version = data.get("config_version")
    if config_version is not None and config_version != 1:
        raise LaunchError(f"Project config key 'config_version' must be 1 in {path}")
    taskledger_dir = data.get("taskledger_dir")
    if taskledger_dir is not None and not isinstance(taskledger_dir, str):
        raise LaunchError(
            f"Project config key 'taskledger_dir' must be a string in {path}"
        )
    artifact_rules = data.get("artifact_rules")
    if artifact_rules is not None:
        if not isinstance(artifact_rules, dict):
            raise LaunchError(
                f"Project config key 'artifact_rules' must be a table in {path}"
            )
        parsed_rules = _artifact_rules_from_mapping(artifact_rules, path=path)
        default_order = data.get("default_artifact_order")
        default_artifact_order = (
            tuple(default_order) if isinstance(default_order, list) else ()
        )
        _validate_artifact_order_and_dependencies(
            parsed_rules,
            default_artifact_order=default_artifact_order,
            path=path,
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
                memory_ref_field=memory_ref_field,
                label=label,
                description=description,
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


def _artifact_rule_error(name: str, message: str, *, path: Path | None) -> str:
    return _project_config_error(f"Artifact rule '{name}' {message}.", path)


def _project_config_error(message: str, path: Path | None) -> str:
    if path is None:
        return message
    return f"{message} in {path}"
