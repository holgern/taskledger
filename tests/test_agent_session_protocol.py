"""Tests covering the agent session failure patterns identified in the audit.

These tests verify guardrails that prevent common agent misuse:
- lock break no-lock message points to next-action
- plan approval escape hatches require --reason
- plan approval blocks when plan has no todos
- plan command records diagnostics during planning
- validate finish blocks when mandatory criteria are unchecked
"""

from __future__ import annotations

import json
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


def _json(result) -> dict[str, object]:
    return json.loads(result.stdout)


def _prepare_proposed_plan_with_todos(
    tmp_path: Path,
    *,
    criterion: str = "Must pass.",
    todo: str = "Fix the thing.",
) -> None:
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "test-task",
                "--description",
                "Test task.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "test-task"],
        ).exit_code
        == 0
    )
    plan_body = (
        "---\n"
        "acceptance_criteria:\n"
        f'  - text: "{criterion}"\n'
        "todos:\n"
        f'  - text: "{todo}"\n'
        "---\n\n"
        "# Plan\n\nFix things.\n"
    )
    command = [
        "--cwd",
        str(tmp_path),
        "plan",
        "propose",
        "--task",
        "test-task",
        "--text",
        plan_body,
    ]
    assert runner.invoke(app, command).exit_code == 0


def _prepare_proposed_plan_no_todos(
    tmp_path: Path,
    *,
    criterion: str = "Must pass.",
) -> None:
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "test-task",
                "--description",
                "Test task.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "test-task"],
        ).exit_code
        == 0
    )
    command = [
        "--cwd",
        str(tmp_path),
        "plan",
        "propose",
        "--task",
        "test-task",
        "--text",
        "Fix things.",
        "--criterion",
        criterion,
    ]
    assert runner.invoke(app, command).exit_code == 0


# --- Lock break no-lock message ---


def test_lock_break_no_lock_message_mentions_next_action(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "lock-test",
                "--description",
                "Lock test.",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "lock",
            "break",
            "--task",
            "lock-test",
            "--reason",
            "testing",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    message = payload["error"]["message"]
    assert "next-action" in message.lower() or "next_action" in message.lower()


def test_plan_propose_releases_planning_lock(tmp_path: Path) -> None:
    """After plan propose, no planning lock should exist."""
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "lock-rel",
                "--description",
                "Lock release test.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "lock-rel"]
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
                "--task",
                "lock-rel",
                "--text",
                "---\n"
                "acceptance_criteria:\n"
                '  - text: "Pass."\n'
                "todos:\n"
                '  - text: "Do it."\n'
                "---\n\n"
                "# Plan\n\nPlan text.\n",
            ],
        ).exit_code
        == 0
    )

    lock_show = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "lock", "show"])
    if lock_show.exit_code == 0:
        payload = _json(lock_show)
        # No active lock should exist after plan propose
        assert (
            payload.get("lock") is None or payload.get("result", {}).get("lock") is None
        )


# --- Escape hatch reason requirements ---


def test_allow_empty_criteria_requires_reason(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--allow-empty-criteria",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert "reason" in payload["error"]["message"].lower()


def test_allow_open_questions_requires_reason(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--allow-open-questions",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert "reason" in payload["error"]["message"].lower()


def test_allow_empty_criteria_with_reason_succeeds(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--reason",
            "testing escape hatch",
            "--allow-empty-criteria",
        ],
    )
    assert result.exit_code == 0


# --- Empty todos gate ---


def test_plan_approval_blocks_when_no_todos(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_no_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    message = payload["error"]["message"].lower()
    assert "todo" in message


def test_plan_approval_empty_todos_with_reason_succeeds(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_no_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--allow-empty-todos",
            "--reason",
            "trivial task",
        ],
    )
    assert result.exit_code == 0


def test_plan_approval_empty_todos_without_reason_fails(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_no_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--allow-empty-todos",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert "reason" in payload["error"]["message"].lower()


# --- Plan command ---


def test_plan_command_records_exit_code(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "cmd-test",
                "--description",
                "Command test.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "cmd-test"]
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "command",
            "--task",
            "cmd-test",
            "--",
            "echo",
            "hello",
        ],
    )
    payload = _json(result)
    assert result.exit_code == 0
    assert payload["result"]["exit_code"] == 0


def test_plan_command_fails_without_active_planning(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "cmd-fail",
                "--description",
                "Command fail test.",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "command",
            "--task",
            "cmd-fail",
            "--",
            "echo",
            "hello",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False


# --- Validation finish gate ---


def test_validate_finish_passed_blocks_unchecked_mandatory_criteria(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "--task",
                "test-task",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "approved",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "start", "--task", "test-task"],
        ).exit_code
        == 0
    )
    # Mark the plan-materialized todo done so implement finish can pass
    todo_list_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "todo", "list", "--task", "test-task"],
    )
    todo_payload = _json(todo_list_result)
    todos = todo_payload["result"]["todos"]
    todo_id = todos[0]["id"]
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo",
                "done",
                todo_id,
                "--task",
                "test-task",
                "--evidence",
                "done",
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
                "--task",
                "test-task",
                "--summary",
                "done",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "validate", "start", "--task", "test-task"],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate",
            "finish",
            "--task",
            "test-task",
            "--result",
            "passed",
            "--summary",
            "passed",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert (
        "incomplete" in payload["error"]["message"].lower()
        or "mandatory" in payload["error"]["message"].lower()
    )


# --- --no-materialize-todos reason gate ---


def test_no_materialize_todos_without_reason_fails(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--no-materialize-todos",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert "reason" in payload["error"]["message"].lower()


def test_no_materialize_todos_with_reason_succeeds(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "approve",
            "--task",
            "test-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "approved",
            "--no-materialize-todos",
            "--reason",
            "trivial task; checklist not needed",
        ],
    )
    assert result.exit_code == 0


# --- Todo source inference ---


def test_todo_added_during_implementation_is_implementer_sourced(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan_with_todos(tmp_path)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "--task",
                "test-task",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "approved",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "start", "--task", "test-task"],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "todo",
            "add",
            "--task",
            "test-task",
            "--text",
            "Implementation todo",
        ],
    )
    assert result.exit_code == 0
    payload = _json(result)
    todos = payload["result"]["task"]["todos"]
    added = [t for t in todos if t["text"] == "Implementation todo"]
    assert len(added) == 1
    assert added[0]["source"] == "implementer"


def test_todo_added_during_planning_is_planner_sourced(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "source-test",
                "--description",
                "Source test.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "source-test"],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "todo",
            "add",
            "--task",
            "source-test",
            "--text",
            "Planning todo",
        ],
    )
    assert result.exit_code == 0
    payload = _json(result)
    todos = payload["result"]["task"]["todos"]
    added = [t for t in todos if t["text"] == "Planning todo"]
    assert len(added) == 1
    assert added[0]["source"] == "planner"


def test_todo_added_without_active_stage_defaults_to_user(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "source-default",
                "--description",
                "Source default test.",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "todo",
            "add",
            "--task",
            "source-default",
            "--text",
            "User todo",
        ],
    )
    assert result.exit_code == 0
    payload = _json(result)
    todos = payload["result"]["task"]["todos"]
    added = [t for t in todos if t["text"] == "User todo"]
    assert len(added) == 1
    assert added[0]["source"] == "user"
