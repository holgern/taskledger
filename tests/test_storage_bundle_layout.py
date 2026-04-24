from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from taskledger.cli import app


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def test_task_create_uses_task_bundle_layout(tmp_path: Path) -> None:
    _init_project(tmp_path)

    project_dir = tmp_path / ".taskledger"
    assert (project_dir / "intros").is_dir()
    assert (project_dir / "tasks").is_dir()
    assert (project_dir / "events").is_dir()
    assert (project_dir / "indexes").is_dir()

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "bundle-layout",
            "--description",
            "Verify the bundle layout.",
        ],
    )
    assert result.exit_code == 0, result.stdout

    task_dir = project_dir / "tasks" / "task-0001"
    assert (task_dir / "task.md").is_file()
    assert (task_dir / "todos.yaml").is_file()
    assert (task_dir / "links.yaml").is_file()
    assert (task_dir / "requirements.yaml").is_file()
    assert (task_dir / "plans").is_dir()
    assert (task_dir / "questions").is_dir()
    assert (task_dir / "runs").is_dir()
    assert (task_dir / "changes").is_dir()
    assert (task_dir / "artifacts").is_dir()
    assert (task_dir / "audit").is_dir()

    todos = yaml.safe_load((task_dir / "todos.yaml").read_text(encoding="utf-8"))
    links = yaml.safe_load((task_dir / "links.yaml").read_text(encoding="utf-8"))
    requirements = yaml.safe_load(
        (task_dir / "requirements.yaml").read_text(encoding="utf-8")
    )
    assert todos["object_type"] == "todos"
    assert links["object_type"] == "links"
    assert requirements["object_type"] == "requirements"


def test_task_list_scans_task_markdown_without_indexes(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "scan-layout",
            "--description",
            "Listing should scan task bundles.",
        ],
    )

    indexes_dir = tmp_path / ".taskledger" / "indexes"
    for path in indexes_dir.glob("*.json"):
        path.unlink()

    result = runner.invoke(app, ["--cwd", str(tmp_path), "task", "list"])
    assert result.exit_code == 0, result.stdout
    assert "scan-layout" in result.stdout
