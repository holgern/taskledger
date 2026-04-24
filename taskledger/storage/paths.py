from __future__ import annotations

from pathlib import Path

from taskledger.models import ProjectPaths


def resolve_taskledger_root(workspace_root: Path) -> Path:
    return workspace_root / ".taskledger"


def resolve_project_paths(workspace_root: Path) -> ProjectPaths:
    return project_paths_for_root(
        workspace_root,
        resolve_taskledger_root(workspace_root),
    )


def project_paths_for_root(workspace_root: Path, project_dir: Path) -> ProjectPaths:
    indexes_dir = project_dir / "indexes"
    return ProjectPaths(
        workspace_root=workspace_root,
        project_dir=project_dir,
        config_path=project_dir / "project.toml",
        repos_dir=project_dir / "repos",
        repo_index_path=indexes_dir / "repos.json",
        workflows_dir=project_dir / "workflows",
        workflow_index_path=indexes_dir / "workflows.json",
        memories_dir=project_dir / "memories",
        contexts_dir=project_dir / "contexts",
        context_index_path=indexes_dir / "contexts.json",
        items_dir=project_dir / "items",
        stages_dir=project_dir / "stages",
        stage_index_path=indexes_dir / "stages.json",
        runs_dir=project_dir / "runs",
    )
