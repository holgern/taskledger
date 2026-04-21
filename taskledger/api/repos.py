from __future__ import annotations

from pathlib import Path

from taskledger.api.types import Repo
from taskledger.storage import add_repo as _add_repo
from taskledger.storage import (
    clear_default_execution_repo as _clear_default_execution_repo,
)
from taskledger.storage import load_project_state
from taskledger.storage import load_repos as _load_repos
from taskledger.storage import remove_repo as _remove_repo
from taskledger.storage import resolve_repo as _resolve_repo
from taskledger.storage import resolve_repo_root as _resolve_repo_root
from taskledger.storage import set_default_execution_repo as _set_default_execution_repo
from taskledger.storage import set_repo_role as _set_repo_role


def add_repo(workspace_root: Path, **kwargs) -> Repo:
    return _add_repo(load_project_state(workspace_root).paths, **kwargs)


def list_repos(workspace_root: Path) -> list[Repo]:
    return _load_repos(load_project_state(workspace_root).paths)


def resolve_repo(workspace_root: Path, ref: str) -> Repo:
    return _resolve_repo(load_project_state(workspace_root).paths, ref)


def resolve_repo_root(workspace_root: Path, ref: str) -> Path:
    return _resolve_repo_root(load_project_state(workspace_root).paths, ref)


def remove_repo(workspace_root: Path, ref: str) -> Repo:
    return _remove_repo(load_project_state(workspace_root).paths, ref)


def set_repo_role(workspace_root: Path, ref: str, *, role: str) -> Repo:
    return _set_repo_role(load_project_state(workspace_root).paths, ref, role=role)


def set_default_execution_repo(workspace_root: Path, ref: str) -> Repo:
    return _set_default_execution_repo(load_project_state(workspace_root).paths, ref)


def clear_default_execution_repo(workspace_root: Path) -> None:
    _clear_default_execution_repo(load_project_state(workspace_root).paths)


def register_repo(workspace_root: Path, **kwargs) -> Repo:
    return add_repo(workspace_root, **kwargs)


def show_repo(workspace_root: Path, ref: str) -> Repo:
    return resolve_repo(workspace_root, ref)


def remove_repo_entry(workspace_root: Path, ref: str) -> Repo:
    return remove_repo(workspace_root, ref)


def set_repo_role_entry(workspace_root: Path, ref: str, *, role: str) -> Repo:
    return set_repo_role(workspace_root, ref, role=role)


def set_default_execution_repo_entry(workspace_root: Path, ref: str) -> Repo:
    return set_default_execution_repo(workspace_root, ref)


def clear_default_execution_repo_entry(workspace_root: Path) -> None:
    clear_default_execution_repo(workspace_root)
