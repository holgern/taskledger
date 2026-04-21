from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from taskledger.api.types import ProjectConfig, RunRecord
from taskledger.storage import create_run_dir as _create_run_dir
from taskledger.storage import (
    ensure_project_exists,
    load_project_config_overrides,
    merge_project_config,
)
from taskledger.storage import resolve_repo_root as _resolve_repo_root
from taskledger.storage import save_run_record as _save_run_record


@dataclass(slots=True, frozen=True)
class RunArtifactPaths:
    run_dir: str
    metadata_file: str
    report_file: str | None
    result_file: str | None


def get_effective_project_config(
    workspace_root: Path,
    *,
    base_config: ProjectConfig | None = None,
) -> ProjectConfig:
    paths = ensure_project_exists(workspace_root)
    overrides = load_project_config_overrides(paths)
    return merge_project_config(base_config or ProjectConfig(), overrides)


def create_run_artifact_layout(
    workspace_root: Path,
    *,
    origin: str,
) -> RunArtifactPaths:
    if not origin.strip():
        raise ValueError("Run artifact origin must not be empty.")
    paths = ensure_project_exists(workspace_root)
    _, run_dir = _create_run_dir(paths)
    return RunArtifactPaths(
        run_dir=str(run_dir),
        metadata_file=str(run_dir / "record.json"),
        report_file=None,
        result_file=None,
    )


def save_run_record(
    workspace_root: Path,
    record: RunRecord,
) -> RunRecord:
    paths = ensure_project_exists(workspace_root)
    run_dir = paths.runs_dir / record.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _save_run_record(run_dir, record)
    return record


def resolve_repo_root(workspace_root: Path, repo_ref: str) -> Path:
    return _resolve_repo_root(ensure_project_exists(workspace_root), repo_ref)


__all__ = [
    "RunArtifactPaths",
    "create_run_artifact_layout",
    "get_effective_project_config",
    "resolve_repo_root",
    "save_run_record",
]
