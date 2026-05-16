from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.services.doctor import inspect_v2_project
from taskledger.storage.ledger_config import load_ledger_config
from taskledger.storage.paths import DEFAULT_TASKLEDGER_DIR_NAME, load_project_locator
from taskledger.storage.project_config import update_taskledger_dir
from taskledger.storage.project_identity import (
    load_project_uuid,
    project_name_or_default,
)
from taskledger.storage.task_store import load_active_locks


@dataclass(slots=True, frozen=True)
class StorageLocationReport:
    workspace_root: str
    config_path: str
    taskledger_dir: str
    project_uuid: str | None
    project_name: str
    ledger_ref: str
    inside_workspace: bool
    is_git_repo: bool
    git_root: str | None
    active_lock_count: int
    has_active_locks: bool
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "storage_location_report",
            "workspace_root": self.workspace_root,
            "config_path": self.config_path,
            "taskledger_dir": self.taskledger_dir,
            "project_uuid": self.project_uuid,
            "project_name": self.project_name,
            "ledger_ref": self.ledger_ref,
            "inside_workspace": self.inside_workspace,
            "is_git_repo": self.is_git_repo,
            "git_root": self.git_root,
            "active_lock_count": self.active_lock_count,
            "has_active_locks": self.has_active_locks,
            "warnings": list(self.warnings),
        }


@dataclass(slots=True, frozen=True)
class SyncStatusReport:
    taskledger_dir: str
    git_root: str | None
    relative_path: str | None
    clean: bool
    status_lines: tuple[str, ...]
    active_lock_count: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "storage_sync_status",
            "taskledger_dir": self.taskledger_dir,
            "git_root": self.git_root,
            "relative_path": self.relative_path,
            "clean": self.clean,
            "status_lines": list(self.status_lines),
            "active_lock_count": self.active_lock_count,
            "warnings": list(self.warnings),
        }


@dataclass(slots=True, frozen=True)
class SyncPreflightReport:
    location: StorageLocationReport
    taskledger_dir_exists: bool
    doctor_healthy: bool
    doctor_errors: tuple[str, ...]
    doctor_warnings: tuple[str, ...]
    tracked_in_workspace_git: bool
    git_status_lines: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "storage_sync_preflight",
            "location": self.location.to_dict(),
            "taskledger_dir_exists": self.taskledger_dir_exists,
            "doctor_healthy": self.doctor_healthy,
            "doctor_errors": list(self.doctor_errors),
            "doctor_warnings": list(self.doctor_warnings),
            "tracked_in_workspace_git": self.tracked_in_workspace_git,
            "git_status_lines": list(self.git_status_lines),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True, frozen=True)
class StorageMoveReport:
    source: str
    target: str
    mode: str
    config_path: str
    project_uuid: str | None
    project_name: str
    ledger_ref: str
    inside_workspace: bool
    adopted_existing: bool
    backup_path: str | None
    doctor_healthy: bool
    doctor_errors: tuple[str, ...]
    next_commands: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "storage_move",
            "source": self.source,
            "target": self.target,
            "mode": self.mode,
            "config_path": self.config_path,
            "project_uuid": self.project_uuid,
            "project_name": self.project_name,
            "ledger_ref": self.ledger_ref,
            "inside_workspace": self.inside_workspace,
            "adopted_existing": self.adopted_existing,
            "backup_path": self.backup_path,
            "doctor_healthy": self.doctor_healthy,
            "doctor_errors": list(self.doctor_errors),
            "next_commands": list(self.next_commands),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True, frozen=True)
class SyncCommitReport:
    git_root: str
    relative_path: str
    commit: str
    message: str
    active_lock_count: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "storage_sync_commit",
            "git_root": self.git_root,
            "relative_path": self.relative_path,
            "commit": self.commit,
            "message": self.message,
            "active_lock_count": self.active_lock_count,
            "warnings": list(self.warnings),
        }


def build_storage_location_report(workspace_root: Path) -> StorageLocationReport:
    locator = load_project_locator(workspace_root)
    taskledger_dir = locator.taskledger_dir
    config_path = locator.config_path
    project_uuid = load_project_uuid(config_path)
    project_name = project_name_or_default(
        config_path,
        workspace_root=locator.workspace_root,
    )
    ledger_ref = load_ledger_config(config_path).ref
    inside_workspace = _is_within(taskledger_dir, locator.workspace_root)
    git_root = _git_root(taskledger_dir)
    active_lock_count = _active_lock_count(locator.workspace_root)
    warnings: list[str] = []
    if inside_workspace:
        warnings.append(
            "Resolved taskledger_dir is inside the workspace. "
            "Keep it ignored in source control."
        )
    if active_lock_count:
        warnings.append(f"{active_lock_count} active lock(s) are present.")
    return StorageLocationReport(
        workspace_root=locator.workspace_root.as_posix(),
        config_path=config_path.as_posix(),
        taskledger_dir=taskledger_dir.as_posix(),
        project_uuid=project_uuid,
        project_name=project_name,
        ledger_ref=ledger_ref,
        inside_workspace=inside_workspace,
        is_git_repo=git_root is not None,
        git_root=git_root.as_posix() if git_root is not None else None,
        active_lock_count=active_lock_count,
        has_active_locks=active_lock_count > 0,
        warnings=tuple(warnings),
    )


def build_sync_preflight_report(workspace_root: Path) -> SyncPreflightReport:
    location = build_storage_location_report(workspace_root)
    taskledger_dir = Path(location.taskledger_dir)
    warnings = list(location.warnings)
    doctor_errors: tuple[str, ...]
    doctor_warnings: tuple[str, ...]
    doctor_healthy: bool
    exists = taskledger_dir.exists()
    if exists:
        try:
            doctor = inspect_v2_project(workspace_root)
        except LaunchError as exc:
            doctor_healthy = False
            doctor_errors = (str(exc),)
            doctor_warnings = ()
        else:
            doctor_healthy = bool(doctor["healthy"])
            doctor_errors = tuple(str(item) for item in doctor["errors"])  # type: ignore[attr-defined]
            doctor_warnings = tuple(str(item) for item in doctor["warnings"])  # type: ignore[attr-defined]
    else:
        doctor_healthy = False
        doctor_errors = (
            f"Resolved taskledger_dir does not exist: {taskledger_dir.as_posix()}",
        )
        doctor_warnings = ()
        warnings.append(doctor_errors[0])

    tracked_in_workspace_git = _tracked_in_workspace_git(workspace_root, taskledger_dir)
    if tracked_in_workspace_git:
        warnings.append(
            "Resolved taskledger_dir is inside the source repo and tracked by Git."
        )
    git_status_lines = tuple(_git_status_lines(taskledger_dir))
    return SyncPreflightReport(
        location=location,
        taskledger_dir_exists=exists,
        doctor_healthy=doctor_healthy,
        doctor_errors=doctor_errors,
        doctor_warnings=doctor_warnings,
        tracked_in_workspace_git=tracked_in_workspace_git,
        git_status_lines=git_status_lines,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def move_taskledger_storage(
    workspace_root: Path,
    *,
    target: Path,
    mode: str,
    adopt_existing: bool = False,
    force: bool = False,
) -> StorageMoveReport:
    if mode not in {"copy", "move"}:
        raise LaunchError("mode must be one of: copy, move.")
    locator = load_project_locator(workspace_root)
    source = locator.taskledger_dir
    target_path = _resolve_target(locator.workspace_root, target)
    default_source = locator.workspace_root / DEFAULT_TASKLEDGER_DIR_NAME
    if source == target_path:
        raise LaunchError("Source and target taskledger_dir are identical.")
    if not source.exists():
        raise LaunchError(
            "Current taskledger_dir does not exist: "
            f"{source.as_posix()}. Run taskledger init first."
        )
    if source != default_source and not force:
        raise LaunchError(
            "Current config already points to a non-default taskledger_dir. "
            "Use --force to migrate from an existing external location."
        )
    if target_path.exists():
        if any(target_path.iterdir()):
            if not adopt_existing:
                raise LaunchError(
                    "Target exists and is not empty. "
                    "Use --adopt-existing to point at it explicitly."
                )
        else:
            adopt_existing = False
    if adopt_existing:
        _verify_adoptable_target(target_path)
    else:
        shutil.copytree(source, target_path, dirs_exist_ok=target_path.exists())

    original_config_text = locator.config_path.read_text(encoding="utf-8")
    configured_value = _render_taskledger_dir_value(locator.workspace_root, target_path)
    update_taskledger_dir(locator.config_path, configured_value)
    doctor = inspect_v2_project(locator.workspace_root)
    if not doctor["healthy"]:
        from taskledger.storage.atomic import atomic_write_text

        atomic_write_text(locator.config_path, original_config_text)
        raise LaunchError(
            "taskledger doctor failed after updating taskledger_dir:\n"
            + "\n".join(str(item) for item in doctor["errors"])  # type: ignore[attr-defined]
        )

    backup_path: Path | None = None
    warnings: list[str] = []
    if mode == "move":
        backup_path = _backup_path_for(source)
        source.rename(backup_path)
        warnings.append(
            "Original storage was preserved at "
            f"{backup_path.as_posix()} as a recoverable backup."
        )

    target_git_root = _git_root(target_path)
    next_commands = [
        f"git add {locator.config_path.name}",
    ]
    if target_git_root is not None:
        next_commands.append(f"git -C {target_git_root.as_posix()} status --short")
    return StorageMoveReport(
        source=source.as_posix(),
        target=target_path.as_posix(),
        mode=mode,
        config_path=locator.config_path.as_posix(),
        project_uuid=load_project_uuid(locator.config_path),
        project_name=project_name_or_default(
            locator.config_path,
            workspace_root=locator.workspace_root,
        ),
        ledger_ref=load_ledger_config(locator.config_path).ref,
        inside_workspace=_is_within(target_path, locator.workspace_root),
        adopted_existing=adopt_existing,
        backup_path=backup_path.as_posix() if backup_path is not None else None,
        doctor_healthy=bool(doctor["healthy"]),
        doctor_errors=tuple(str(item) for item in doctor["errors"]),  # type: ignore[attr-defined]
        next_commands=tuple(next_commands),
        warnings=tuple(warnings),
    )


def build_sync_status_report(workspace_root: Path) -> SyncStatusReport:
    location = build_storage_location_report(workspace_root)
    taskledger_dir = Path(location.taskledger_dir)
    git_root = _git_root(taskledger_dir)
    status_lines = tuple(_git_status_lines(taskledger_dir))
    warnings = list(location.warnings)
    if git_root is None:
        warnings.append("Resolved taskledger_dir is not in a Git repository.")
    return SyncStatusReport(
        taskledger_dir=location.taskledger_dir,
        git_root=git_root.as_posix() if git_root is not None else None,
        relative_path=_relative_to(taskledger_dir, git_root) if git_root else None,
        clean=not status_lines,
        status_lines=status_lines,
        active_lock_count=location.active_lock_count,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def sync_commit_storage(workspace_root: Path, *, message: str) -> SyncCommitReport:
    location = build_storage_location_report(workspace_root)
    taskledger_dir = Path(location.taskledger_dir)
    git_root = _git_root(taskledger_dir)
    if git_root is None:
        raise LaunchError("Resolved taskledger_dir is not in a Git repository.")
    relative_path = _relative_to(taskledger_dir, git_root)
    status_lines = _git_status_lines(taskledger_dir)
    if not status_lines:
        raise LaunchError("No local Git changes exist under taskledger_dir.")
    _run_git(git_root, "add", "--all", "--", relative_path)
    _run_git(git_root, "commit", "-m", message, "--", relative_path)
    commit = _run_git(git_root, "rev-parse", "HEAD").stdout.strip()
    warnings: list[str] = []
    if location.active_lock_count:
        warnings.append(f"{location.active_lock_count} active lock(s) were committed.")
    return SyncCommitReport(
        git_root=git_root.as_posix(),
        relative_path=relative_path,
        commit=commit,
        message=message,
        active_lock_count=location.active_lock_count,
        warnings=tuple(warnings),
    )


def _active_lock_count(workspace_root: Path) -> int:
    try:
        return len(load_active_locks(workspace_root))
    except LaunchError:
        return 0


def _resolve_target(workspace_root: Path, target: Path) -> Path:
    expanded = target.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (workspace_root / expanded).resolve()


def _render_taskledger_dir_value(workspace_root: Path, target: Path) -> str:
    try:
        return target.relative_to(workspace_root).as_posix()
    except ValueError:
        return target.as_posix()


def _verify_adoptable_target(target: Path) -> None:
    if not target.exists():
        raise LaunchError("Cannot adopt a missing target directory.")
    if not (target / "storage.yaml").exists():
        raise LaunchError(
            f"Target {target.as_posix()} does not look like a taskledger storage root."
        )


def _backup_path_for(source: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return source.with_name(f"{source.name}.moved-{timestamp}")


def _git_root(path: Path) -> Path | None:
    if not path.exists():
        candidate = path.parent
    else:
        candidate = path
    result = subprocess.run(
        ["git", "-C", candidate.as_posix(), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _tracked_in_workspace_git(workspace_root: Path, taskledger_dir: Path) -> bool:
    if not _is_within(taskledger_dir, workspace_root):
        return False
    git_root = _git_root(workspace_root)
    if git_root is None:
        return False
    relative_path = _relative_to(taskledger_dir, git_root)
    result = _run_git(git_root, "ls-files", "--", relative_path, check=False)
    return bool(result.stdout.strip())


def _git_status_lines(path: Path) -> list[str]:
    git_root = _git_root(path)
    if git_root is None:
        return []
    relative_path = _relative_to(path, git_root)
    result = _run_git(git_root, "status", "--short", "--", relative_path)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _relative_to(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix() or "."
    except ValueError as exc:
        raise LaunchError(
            f"{path.as_posix()} is not inside Git root {root.as_posix()}."
        ) from exc


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _run_git(
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", root.as_posix(), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise LaunchError(
            f"git {' '.join(args)} failed in {root.as_posix()}: "
            f"{stderr or f'exit {result.returncode}'}"
        )
    return result
