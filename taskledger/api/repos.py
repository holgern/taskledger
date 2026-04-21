from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectRepo
from taskledger.storage import (
    add_repo as _add_repo,
)
from taskledger.storage import (
    clear_default_execution_repo as _clear_default_execution_repo,
)
from taskledger.storage import (
    load_project_state,
)
from taskledger.storage import (
    load_repos as _load_repos,
)
from taskledger.storage import (
    remove_repo as _remove_repo,
)
from taskledger.storage import (
    resolve_repo as _resolve_repo,
)
from taskledger.storage import (
    resolve_repo_root as _resolve_repo_root,
)
from taskledger.storage import (
    save_repos as _save_repos,
)
from taskledger.storage import (
    set_default_execution_repo as _set_default_execution_repo,
)
from taskledger.storage import (
    set_repo_role as _set_repo_role,
)


def add_repo(paths, **kwargs) -> ProjectRepo:
    return _add_repo(paths, **kwargs)


def clear_default_execution_repo(paths) -> None:
    _clear_default_execution_repo(paths)


def load_repos(paths) -> list[ProjectRepo]:
    return _load_repos(paths)


def remove_repo(paths, ref: str) -> ProjectRepo:
    return _remove_repo(paths, ref)


def resolve_repo(paths, ref: str) -> ProjectRepo:
    return _resolve_repo(paths, ref)


def resolve_repo_root(paths, ref: str):
    return _resolve_repo_root(paths, ref)


def save_repos(paths, repos: list[ProjectRepo]) -> None:
    _save_repos(paths, repos)


def set_default_execution_repo(paths, ref: str) -> ProjectRepo:
    return _set_default_execution_repo(paths, ref)


def set_repo_role(paths, ref: str, *, role: str) -> ProjectRepo:
    return _set_repo_role(paths, ref, role=role)


def register_repo(workspace_root: Path, **kwargs) -> ProjectRepo:
    return add_repo(load_project_state(workspace_root).paths, **kwargs)


def list_repos(workspace_root: Path) -> list[ProjectRepo]:
    return load_repos(load_project_state(workspace_root).paths)


def show_repo(workspace_root: Path, ref: str) -> ProjectRepo:
    return resolve_repo(load_project_state(workspace_root).paths, ref)


def remove_repo_entry(workspace_root: Path, ref: str) -> ProjectRepo:
    return remove_repo(load_project_state(workspace_root).paths, ref)


def set_repo_role_entry(workspace_root: Path, ref: str, *, role: str) -> ProjectRepo:
    return set_repo_role(load_project_state(workspace_root).paths, ref, role=role)


def set_default_execution_repo_entry(workspace_root: Path, ref: str) -> ProjectRepo:
    return set_default_execution_repo(load_project_state(workspace_root).paths, ref)


def clear_default_execution_repo_entry(workspace_root: Path) -> None:
    clear_default_execution_repo(load_project_state(workspace_root).paths)
