from __future__ import annotations

import json
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


def test_v2_task_lifecycle_and_handoff(tmp_path: Path) -> None:
    _init_project(tmp_path)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "rewrite-v2",
                "--title",
                "Rewrite V2",
                "--description",
                "Rewrite taskledger to the new design.",
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "can", "rewrite-v2", "plan"],
    ).stdout
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "rewrite-v2"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "add",
                "rewrite-v2",
                "--text",
                "Should exports include v2?",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "answer",
                "rewrite-v2",
                "q-1",
                "--text",
                "Yes.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "propose",
                "rewrite-v2",
                "--text",
                "## Goal\n\nShip the v2 rewrite.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "rewrite-v2",
                "--version",
                "1",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "start", "rewrite-v2"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "log",
                "rewrite-v2",
                "--message",
                "wired new storage",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "add-change",
                "rewrite-v2",
                "--path",
                "taskledger/storage/v2.py",
                "--kind",
                "edit",
                "--summary",
                "Added canonical v2 storage.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "finish",
                "rewrite-v2",
                "--summary",
                "Implemented v2",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "validate", "start", "rewrite-v2"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate",
                "add-check",
                "rewrite-v2",
                "--name",
                "tests pass",
                "--status",
                "pass",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate",
                "finish",
                "rewrite-v2",
                "--result",
                "passed",
                "--summary",
                "Validated v2",
            ],
        ).exit_code
        == 0
    )

    show_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "task", "show", "rewrite-v2"],
    )
    assert show_result.exit_code == 0
    payload = json.loads(show_result.stdout)
    assert payload["task"]["status_stage"] == "done"
    assert payload["task"]["accepted_plan_version"] == 1
    assert payload["changes"][0]["path"] == "taskledger/storage/v2.py"

    handoff_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "handoff",
            "validation-context",
            "rewrite-v2",
        ],
    )
    assert handoff_result.exit_code == 0
    assert "Code Changes" in handoff_result.stdout
    assert "taskledger/storage/v2.py" in handoff_result.stdout

    doctor_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "doctor"],
    )
    assert doctor_result.exit_code == 0
    doctor_payload = json.loads(doctor_result.stdout)
    assert doctor_payload["healthy"] is True

    reindex_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "reindex"],
    )
    assert reindex_result.exit_code == 0
    reindex_payload = json.loads(reindex_result.stdout)
    assert reindex_payload["counts"]["tasks"] == 1


def test_v2_lock_break_and_expired_lock_report(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "lock-task",
            "--description",
            "Task with a planning lock.",
        ],
    )
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "lock-task"])

    lock_path = tmp_path / ".taskledger" / "tasks" / "task-1.lock.yaml"
    payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    payload["expires_at"] = "2000-01-01T00:00:00+00:00"
    lock_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    doctor_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "doctor", "locks"],
    )
    assert doctor_result.exit_code == 0
    assert "task-1" in doctor_result.stdout

    break_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "lock",
            "break",
            "lock-task",
            "--reason",
            "recover stale planning lock",
        ],
    )
    assert break_result.exit_code == 0
    assert json.loads(break_result.stdout)["command"] == "lock break"
    assert not lock_path.exists()


def test_task_first_support_commands_are_available(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "support-task",
                "--description",
                "Exercise task-first support commands.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo",
                "add",
                "support-task",
                "--text",
                "write docs",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "file",
                "link",
                "support-task",
                "--path",
                "README.md",
                "--kind",
                "doc",
            ],
        ).exit_code
        == 0
    )

    todo_show = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "todo", "show", "support-task", "todo-1"],
    )
    assert todo_show.exit_code == 0
    assert json.loads(todo_show.stdout)["todo"]["id"] == "todo-1"

    file_list = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "file", "list", "support-task"],
    )
    assert file_list.exit_code == 0
    assert "@README.md [doc]" in file_list.stdout
