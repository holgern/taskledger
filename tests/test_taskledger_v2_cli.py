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


def _json(result) -> dict[str, object]:
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    return payload


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
    payload = _json(show_result)
    assert payload["operation"] == "task.show"
    assert payload["data"]["task"]["status_stage"] == "done"
    assert payload["data"]["task"]["accepted_plan_version"] == 1
    assert payload["data"]["changes"][0]["path"] == "taskledger/storage/v2.py"

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
    doctor_payload = _json(doctor_result)
    assert doctor_payload["data"]["healthy"] is True

    reindex_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "reindex"],
    )
    reindex_payload = _json(reindex_result)
    assert reindex_payload["data"]["counts"]["tasks"] == 1


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
    assert _json(break_result)["data"]["command"] == "lock break"
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
    assert _json(todo_show)["data"]["todo"]["id"] == "todo-1"

    file_list = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "file", "list", "support-task"],
    )
    assert file_list.exit_code == 0
    assert "@README.md [doc]" in file_list.stdout


def test_root_alias_uses_stable_json_envelope(tmp_path: Path) -> None:
    init_result = runner.invoke(app, ["--root", str(tmp_path), "init"])
    assert init_result.exit_code == 0

    create_result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--json",
            "task",
            "create",
            "root-alias-task",
            "--description",
            "Exercise the root alias.",
        ],
    )
    payload = _json(create_result)
    assert payload["operation"] == "task.create"
    assert payload["result_type"] == "task"
    assert payload["data"]["slug"] == "root-alias-task"


def test_plan_approval_blocks_open_questions_with_json_error(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "question-blocked",
            "--description",
            "Approval should fail while a question is open.",
        ],
    )
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "question-blocked"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "question",
            "add",
            "question-blocked",
            "--text",
            "Need one more decision?",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "propose",
            "question-blocked",
            "--text",
            "## Goal\n\nAnswer the question first.\n",
        ],
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "question-blocked",
            "--version",
            "1",
        ],
    )
    assert result.exit_code == 21
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert payload["operation"] == "plan.approve"
    assert payload["error_type"] == "ApprovalRequired"


def test_expired_lock_requires_explicit_break_json_error(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "stale-lock-task",
            "--description",
            "Expired locks must be broken explicitly.",
        ],
    )
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "stale-lock-task"])

    lock_path = tmp_path / ".taskledger" / "tasks" / "task-1.lock.yaml"
    payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    payload["expires_at"] = "2000-01-01T00:00:00+00:00"
    lock_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "propose",
            "stale-lock-task",
            "--text",
            "## Goal\n\nDo not silently replace stale locks.\n",
        ],
    )
    assert result.exit_code == 31
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert payload["error_type"] == "StaleLockRequiresBreak"
