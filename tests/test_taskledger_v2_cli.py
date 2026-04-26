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
    assert payload["ok"] is True
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
                "Rewrite V2",
                "--slug",
                "rewrite-v2",
                "--description",
                "Rewrite taskledger to the new design.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "rewrite-v2"],
        ).exit_code
        == 0
    )
    assert runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "can", "plan"],
    ).stdout
    start_plan = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "start", "--task", "rewrite-v2"],
        )
    )
    assert start_plan["result"]["status_stage"] == "draft"
    assert start_plan["result"]["active_stage"] == "planning"
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "add",
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
                "q-0001",
                "--text",
                "Yes.",
            ],
        ).exit_code
        == 0
    )
    propose_plan = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan", "propose", "--task", "rewrite-v2",
                "--criterion",
                "Ship the rewrite safely.",
                "--text",
                "## Goal\n\nShip the v2 rewrite.",
            ],
        )
    )
    assert propose_plan["result"]["status_stage"] == "plan_review"
    assert propose_plan["result"]["active_stage"] is None
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "approve", "--task", "rewrite-v2",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Ready to implement.",
                "--allow-empty-todos",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )
    start_impl = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "implement", "start", "--task", "rewrite-v2"],
        )
    )
    assert start_impl["result"]["status_stage"] == "approved"
    assert start_impl["result"]["active_stage"] == "implementation"
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement", "log", "--task", "rewrite-v2",
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
                    "change",
                    "--task",
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
    finish_impl = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "implement", "finish", "--task", "rewrite-v2",
                "--summary",
                "Implemented v2",
            ],
        )
    )
    assert finish_impl["result"]["status_stage"] == "implemented"
    assert finish_impl["result"]["active_stage"] is None
    start_validation = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "validate", "start", "--task", "rewrite-v2"],
        )
    )
    assert start_validation["result"]["status_stage"] == "implemented"
    assert start_validation["result"]["active_stage"] == "validation"
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate", "check", "--task", "rewrite-v2",
                "--criterion",
                "ac-0001",
                "--status",
                "pass",
                "--evidence",
                "pytest -q",
            ],
        ).exit_code
        == 0
    )
    finish_validation = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "validate", "finish", "--task", "rewrite-v2",
                "--result",
                "passed",
                "--summary",
                "Validated v2",
            ],
        )
    )
    assert finish_validation["result"]["status_stage"] == "done"
    assert finish_validation["result"]["active_stage"] is None

    show_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "task", "show", "--task", "rewrite-v2"],
    )
    payload = _json(show_result)
    assert payload["command"] == "task.show"
    assert payload["result"]["task"]["status_stage"] == "done"
    assert payload["result"]["task"]["active_stage"] is None
    assert payload["result"]["task"]["accepted_plan_version"] == 1
    assert payload["result"]["changes"][0]["path"] == "taskledger/storage/v2.py"

    handoff_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "handoff",
            "validation-context",
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
    assert doctor_payload["result"]["healthy"] is True

    reindex_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "reindex"],
    )
    reindex_payload = _json(reindex_result)
    assert reindex_payload["result"]["counts"]["tasks"] == 1


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
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "--task", "lock-task"])

    lock_path = tmp_path / ".taskledger" / "tasks" / "task-0001" / "lock.yaml"
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
    assert "task-0001" in doctor_result.stdout

    break_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "lock",
            "break",
            "--reason",
            "recover stale planning lock",
            "--task",
            "lock-task",
        ],
    )
    assert break_result.exit_code == 0
    assert _json(break_result)["result"]["command"] == "lock break"
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
            ["--cwd", str(tmp_path), "task", "activate", "support-task"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo", "add", "--text",
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
                "add",
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
        ["--cwd", str(tmp_path), "--json", "todo", "show", "todo-0001"],
    )
    assert _json(todo_show)["result"]["todo"]["id"] == "todo-0001"

    file_list = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "file", "list"],
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
    assert payload["command"] == "task.create"
    assert payload["result"]["slug"] == "root-alias-task"


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
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "--task", "question-blocked"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "question",
            "add",
            "--text",
            "Need one more decision?",
            "--task",
            "question-blocked",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan", "propose", "--task", "question-blocked",
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
            "plan", "approve", "--task", "question-blocked",
            "--version",
            "1",
        ],
    )
    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "plan.approve"
    assert payload["error"]["code"] == "WORKFLOW_REJECTION"


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
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "--task", "stale-lock-task"])

    lock_path = tmp_path / ".taskledger" / "tasks" / "task-0001" / "lock.yaml"
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
            "plan", "propose", "--task", "stale-lock-task",
            "--text",
            "## Goal\n\nDo not silently replace stale locks.\n",
        ],
    )
    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "STALE_LOCK_REQUIRES_BREAK"
