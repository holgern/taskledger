from __future__ import annotations

import yaml
from pathlib import Path

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


def test_todos_links_and_requirements_live_in_sidecars(tmp_path: Path) -> None:
    _init_project(tmp_path)

    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "dependency-task",
            "--description",
            "Dependency target.",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "sidecar-task",
            "--description",
            "Verify sidecar-backed collections.",
        ],
    )

    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "todo",
            "add",
            "sidecar-task",
            "--text",
            "Write sidecar test.",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "file",
            "link",
            "sidecar-task",
            "--path",
            "README.md",
            "--kind",
            "doc",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "require",
            "add",
            "sidecar-task",
            "dependency-task",
        ],
    )

    task_dir = tmp_path / ".taskledger" / "tasks" / "task-2"
    task_markdown = (task_dir / "task.md").read_text(encoding="utf-8")
    assert "todos:" not in task_markdown
    assert "file_links:" not in task_markdown
    assert "requirements:" not in task_markdown

    todos = yaml.safe_load((task_dir / "todos.yaml").read_text(encoding="utf-8"))
    links = yaml.safe_load((task_dir / "links.yaml").read_text(encoding="utf-8"))
    requirements = yaml.safe_load(
        (task_dir / "requirements.yaml").read_text(encoding="utf-8")
    )
    assert todos["todos"][0]["text"] == "Write sidecar test."
    assert links["links"][0]["path"] == "README.md"
    assert requirements["requirements"][0]["task_id"] == "task-1"

    result = runner.invoke(app, ["--cwd", str(tmp_path), "task", "show", "sidecar-task"])
    assert result.exit_code == 0, result.stdout
    assert "sidecar-task" in result.stdout
