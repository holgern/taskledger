from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from taskledger.storage.project_config import load_project_config_document

CANONICAL_PROJECT_CONFIG_FILENAME = "taskledger.toml"
PROJECT_CONFIG_FILENAMES = (".taskledger.toml", CANONICAL_PROJECT_CONFIG_FILENAME)
DEFAULT_TASKLEDGER_DIR_NAME = ".taskledger"
LEGACY_PROJECT_CONFIG_FILENAME = "project.toml"


@dataclass(slots=True, frozen=True)
class ProjectLocator:
    workspace_root: Path
    config_path: Path
    taskledger_dir: Path
    source: Literal["explicit", "dotfile", "toml", "legacy", "default"]


@dataclass(slots=True, frozen=True)
class ProjectPaths:
    workspace_root: Path
    project_dir: Path
    taskledger_dir: Path
    config_path: Path
    repos_dir: Path
    repo_index_path: Path


def resolve_taskledger_root(workspace_root: Path) -> Path:
    return load_project_locator(workspace_root).taskledger_dir


def resolve_project_paths(workspace_root: Path) -> ProjectPaths:
    locator = load_project_locator(workspace_root)
    return project_paths_for_root(
        locator.workspace_root,
        locator.taskledger_dir,
        config_path=locator.config_path,
    )


def discover_workspace_root(start: Path) -> Path:
    return load_project_locator(start).workspace_root


def find_project_config(start: Path) -> Path | None:
    for current in _search_roots(start):
        for filename in PROJECT_CONFIG_FILENAMES:
            candidate = current / filename
            if candidate.exists():
                return candidate
    return None


def load_project_locator(
    start: Path,
    *,
    taskledger_dir_override: Path | None = None,
    config_filename: str = CANONICAL_PROJECT_CONFIG_FILENAME,
) -> ProjectLocator:
    start_path = start.expanduser().resolve()
    config_path = find_project_config(start_path)
    if config_path is not None:
        workspace_root = config_path.parent
        taskledger_dir = (
            _resolve_path(taskledger_dir_override, workspace_root=workspace_root)
            if taskledger_dir_override is not None
            else _taskledger_dir_from_config(config_path, workspace_root=workspace_root)
        )
        return ProjectLocator(
            workspace_root=workspace_root,
            config_path=config_path,
            taskledger_dir=taskledger_dir,
            source=(
                "explicit"
                if taskledger_dir_override is not None
                else "dotfile"
                if config_path.name.startswith(".")
                else "toml"
            ),
        )

    legacy_workspace_root = _find_legacy_workspace_root(start_path)
    if legacy_workspace_root is not None:
        legacy_config_path = (
            legacy_workspace_root
            / DEFAULT_TASKLEDGER_DIR_NAME
            / LEGACY_PROJECT_CONFIG_FILENAME
        )
        workspace_root = legacy_workspace_root
        return ProjectLocator(
            workspace_root=workspace_root,
            config_path=(
                legacy_config_path
                if legacy_config_path.exists()
                else workspace_root / config_filename
            ),
            taskledger_dir=(
                _resolve_path(taskledger_dir_override, workspace_root=workspace_root)
                if taskledger_dir_override is not None
                else workspace_root / DEFAULT_TASKLEDGER_DIR_NAME
            ),
            source="explicit" if taskledger_dir_override is not None else "legacy",
        )

    workspace_root = start_path
    return ProjectLocator(
        workspace_root=workspace_root,
        config_path=workspace_root / config_filename,
        taskledger_dir=(
            _resolve_path(taskledger_dir_override, workspace_root=workspace_root)
            if taskledger_dir_override is not None
            else workspace_root / DEFAULT_TASKLEDGER_DIR_NAME
        ),
        source="explicit" if taskledger_dir_override is not None else "default",
    )


def project_paths_for_root(
    workspace_root: Path,
    project_dir: Path,
    *,
    config_path: Path | None = None,
) -> ProjectPaths:
    indexes_dir = project_dir / "indexes"
    return ProjectPaths(
        workspace_root=workspace_root,
        project_dir=project_dir,
        taskledger_dir=project_dir,
        config_path=config_path or workspace_root / CANONICAL_PROJECT_CONFIG_FILENAME,
        repos_dir=project_dir / "repos",
        repo_index_path=indexes_dir / "repos.json",
    )


def _search_roots(start: Path) -> tuple[Path, ...]:
    current = start if start.is_dir() else start.parent
    return (current, *current.parents)


def _find_legacy_workspace_root(start: Path) -> Path | None:
    for current in _search_roots(start):
        if (current / DEFAULT_TASKLEDGER_DIR_NAME / "storage.yaml").exists():
            return current
    return None


def _taskledger_dir_from_config(config_path: Path, *, workspace_root: Path) -> Path:
    document = load_project_config_document(config_path)
    raw_value = document.get("taskledger_dir")
    if not isinstance(raw_value, str) or not raw_value.strip():
        return workspace_root / DEFAULT_TASKLEDGER_DIR_NAME
    return _resolve_path(raw_value, workspace_root=workspace_root)


def _resolve_path(value: str | Path, *, workspace_root: Path) -> Path:
    raw_value = os.path.expandvars(os.fspath(value))
    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()
