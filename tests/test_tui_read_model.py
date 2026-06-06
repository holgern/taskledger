"""Tests for taskledger.services.tui_read_model.

These tests do not import Textual. They exercise the pure aggregation
function so the TUI presenter can stay thin.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.services.tui_read_model import load_tui_snapshot


def _init_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0, result.stdout


def _create_task(tmp_path: Path, title: str, *, slug: str | None = None) -> None:
    runner = CliRunner()
    args = ["--cwd", str(tmp_path), "task", "create", title]
    if slug is not None:
        args.extend(["--slug", slug])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.stdout


def test_tui_snapshot_kind_and_tasks_empty(tmp_path: Path) -> None:
    _init_workspace(tmp_path)

    payload = load_tui_snapshot(tmp_path)

    assert payload["kind"] == "tui_snapshot"
    assert payload["tasks"] == []
    assert payload["archived_tasks"] == []
    assert payload["selected"] is None
    assert payload["plan_review_markdown"] is None
    assert payload["report_markdown"] is None
    assert payload["reviews"] == []
    assert payload["include_archived"] is False


def test_tui_snapshot_lists_visible_tasks(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    _create_task(tmp_path, "First TUI task", slug="first-tui-task")
    _create_task(tmp_path, "Second TUI task", slug="second-tui-task")

    payload = load_tui_snapshot(tmp_path)

    assert payload["kind"] == "tui_snapshot"
    tasks = payload["tasks"]
    assert len(tasks) == 2
    assert {task["id"] for task in tasks} == {"task-0001", "task-0002"}
    assert all(task["status_stage"] == "draft" for task in tasks)


def test_tui_snapshot_resolves_selected_task_by_ref(tmp_path: Path) -> None:
    _init_workspace(tmp_path)
    _create_task(
        tmp_path,
        "Selected TUI task",
        slug="selected-tui-task",
    )

    payload = load_tui_snapshot(tmp_path, task_ref="task-0001")

    selected = payload["selected"]
    assert selected is not None
    task = selected["task"]
    assert task["id"] == "task-0001"
    assert task["slug"] == "selected-tui-task"
    # report_markdown is always generated for a selected task.
    assert isinstance(payload["report_markdown"], str)
    assert "task-0001" in payload["report_markdown"]
    # No proposed plan in 'new' stage -> plan review renderer raises
    # LaunchError; aggregator swallows it and reports None.
    assert payload["plan_review_markdown"] is None
    assert payload["reviews"] == []


def test_tui_snapshot_no_selected_when_ref_and_active_missing(
    tmp_path: Path,
) -> None:
    _init_workspace(tmp_path)
    _create_task(tmp_path, "Lonely task", slug="lonely-task")

    payload = load_tui_snapshot(tmp_path)

    assert payload["selected"] is None
    assert payload["plan_review_markdown"] is None
    assert payload["report_markdown"] is None
    assert payload["reviews"] == []


def test_tui_snapshot_include_archived_keeps_visible_separate(
    tmp_path: Path,
) -> None:
    _init_workspace(tmp_path)
    _create_task(tmp_path, "Kept visible", slug="kept-visible")
    _create_task(tmp_path, "Will be archived", slug="to-archive")

    runner = CliRunner()
    archive_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "archive",
            "task-0002",
            "--reason",
            "Smoke test for archive toggle.",
            "--force",
        ],
    )
    assert archive_result.exit_code == 0, archive_result.stdout

    default_payload = load_tui_snapshot(tmp_path)
    assert [task["id"] for task in default_payload["tasks"]] == ["task-0001"]
    assert default_payload["archived_tasks"] == []

    archived_payload = load_tui_snapshot(tmp_path, include_archived=True)
    assert [task["id"] for task in archived_payload["tasks"]] == ["task-0001"]
    assert [task["id"] for task in archived_payload["archived_tasks"]] == ["task-0002"]
    assert archived_payload["include_archived"] is True
    assert archived_payload["archived_tasks"][0]["archived"] is True
