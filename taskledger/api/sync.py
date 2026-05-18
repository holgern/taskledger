from __future__ import annotations

from pathlib import Path

from taskledger.services.git_sync import (
    git_hooks_status as _git_hooks_status,
)
from taskledger.services.git_sync import (
    git_sync as _git_sync,
)
from taskledger.services.git_sync import (
    git_sync_commit as _git_sync_commit,
)
from taskledger.services.git_sync import (
    git_sync_export_local as _git_sync_export_local,
)
from taskledger.services.git_sync import (
    git_sync_import_local as _git_sync_import_local,
)
from taskledger.services.git_sync import (
    git_sync_paths as _git_sync_paths,
)
from taskledger.services.git_sync import (
    git_sync_pull as _git_sync_pull,
)
from taskledger.services.git_sync import (
    git_sync_push as _git_sync_push,
)
from taskledger.services.git_sync import (
    git_sync_status as _git_sync_status,
)
from taskledger.services.git_sync import (
    init_git_sync_repo as _init_git_sync_repo,
)
from taskledger.services.git_sync import (
    install_git_hooks as _install_git_hooks,
)
from taskledger.services.git_sync import (
    uninstall_git_hooks as _uninstall_git_hooks,
)


def sync_git_init(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    remote_url: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    project_path: str | None = None,
    adopt_existing: bool = False,
    mode: str = "move",
    install_hooks: bool = False,
    force_hooks: bool = False,
) -> dict[str, object]:
    return _init_git_sync_repo(
        workspace_root,
        repo=repo,
        remote_url=remote_url,
        remote=remote,
        branch=branch,
        project_path=project_path,
        adopt_existing=adopt_existing,
        mode=mode,
        install_hooks=install_hooks,
        force_hooks=force_hooks,
    )


def sync_git_paths(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
) -> dict[str, object]:
    return _git_sync_paths(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
    )


def sync_git_status(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
) -> dict[str, object]:
    return _git_sync_status(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
    )


def sync_git_import_local(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    return _git_sync_import_local(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        dry_run=dry_run,
    )


def sync_git_commit(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    message: str | None = None,
    allow_active_locks: bool = False,
) -> dict[str, object]:
    return _git_sync_commit(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        message=message,
        allow_active_locks=allow_active_locks,
    )


def sync_git_export_local(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    message: str | None = None,
    allow_dirty: bool = False,
    allow_active_locks: bool = False,
) -> dict[str, object]:
    return _git_sync_export_local(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        message=message,
        allow_dirty=allow_dirty,
        allow_active_locks=allow_active_locks,
    )


def sync_git_pull(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    allow_dirty: bool = False,
) -> dict[str, object]:
    return _git_sync_pull(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        allow_dirty=allow_dirty,
    )


def sync_git_push(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    message: str | None = None,
    allow_dirty: bool = False,
    allow_active_locks: bool = False,
) -> dict[str, object]:
    return _git_sync_push(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        message=message,
        allow_dirty=allow_dirty,
        allow_active_locks=allow_active_locks,
    )


def sync_git_sync(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    message: str | None = None,
    allow_dirty: bool = False,
    allow_active_locks: bool = False,
) -> dict[str, object]:
    return _git_sync(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        message=message,
        allow_dirty=allow_dirty,
        allow_active_locks=allow_active_locks,
    )


def sync_git_hooks_install(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
    force: bool = False,
    quiet: bool = False,
) -> dict[str, object]:
    return _install_git_hooks(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
        force=force,
        quiet=quiet,
    )


def sync_git_hooks_status(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
) -> dict[str, object]:
    return _git_hooks_status(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
    )


def sync_git_hooks_uninstall(
    workspace_root: Path,
    *,
    repo: Path | None = None,
    project_path: str | None = None,
    remote: str | None = None,
    branch: str | None = None,
) -> dict[str, object]:
    return _uninstall_git_hooks(
        workspace_root,
        repo=repo,
        project_path=project_path,
        remote=remote,
        branch=branch,
    )


__all__ = [
    "sync_git_commit",
    "sync_git_export_local",
    "sync_git_hooks_install",
    "sync_git_hooks_status",
    "sync_git_hooks_uninstall",
    "sync_git_import_local",
    "sync_git_init",
    "sync_git_paths",
    "sync_git_pull",
    "sync_git_push",
    "sync_git_status",
    "sync_git_sync",
]
