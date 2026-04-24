from __future__ import annotations

from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths
from taskledger.storage.common import write_text
from taskledger.storage.paths import project_paths_for_root, resolve_taskledger_root
from taskledger.storage.project_config import DEFAULT_PROJECT_TOML


def init_project_state(workspace_root: Path) -> tuple[ProjectPaths, list[str]]:
    paths = project_paths_for_root(
        workspace_root,
        resolve_taskledger_root(workspace_root),
    )
    created: list[str] = []
    for directory in (
        paths.project_dir,
        paths.project_dir / "intros",
        paths.project_dir / "tasks",
        paths.project_dir / "events",
        paths.project_dir / "indexes",
    ):
        if directory.exists():
            continue
        directory.mkdir(parents=True, exist_ok=True)
        created.append(str(directory))
    for path, contents in (
        (paths.config_path, DEFAULT_PROJECT_TOML),
        (paths.repo_index_path, "[]\n"),
        (paths.project_dir / "indexes" / "tasks.json", "[]\n"),
        (paths.project_dir / "indexes" / "active_locks.json", "[]\n"),
        (paths.project_dir / "indexes" / "dependencies.json", "[]\n"),
        (paths.project_dir / "indexes" / "introductions.json", "[]\n"),
        (paths.project_dir / "indexes" / "latest_runs.json", "[]\n"),
        (paths.project_dir / "indexes" / "plan_versions.json", "[]\n"),
    ):
        if path.exists():
            continue
        write_text(path, contents)
        created.append(str(path))
    return paths, created


def ensure_project_exists(workspace_root: Path) -> ProjectPaths:
    paths = project_paths_for_root(
        workspace_root,
        resolve_taskledger_root(workspace_root),
    )
    _reject_legacy_item_memory_indexes(paths)
    missing = [
        path
        for path in (
            paths.config_path,
            paths.project_dir / "tasks",
            paths.project_dir / "intros",
            paths.project_dir / "events",
            paths.project_dir / "indexes",
        )
        if not path.exists()
    ]
    if missing:
        raise LaunchError(
            "Project state is not initialized. Run 'taskledger init' first."
        )
    _ensure_additive_project_files(paths)
    return paths


def _ensure_additive_project_files(paths: ProjectPaths) -> None:
    for directory in (
        paths.project_dir,
        paths.project_dir / "intros",
        paths.project_dir / "tasks",
        paths.project_dir / "events",
        paths.project_dir / "indexes",
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
        paths.project_dir / "indexes" / "latest_runs.json",
        paths.project_dir / "indexes" / "plan_versions.json",
    ):
        if path.exists():
            continue
        write_text(path, "[]\n")


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
