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


def test_json_success_envelope_uses_ok_command_result_and_events(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "task",
            "create",
            "json-contract-task",
            "--description",
            "Verify the stable JSON success envelope.",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "command": "task.create",
        "task_id": "task-0001",
        "result": payload["result"],
        "events": [],
    }
    assert payload["result"]["slug"] == "json-contract-task"


def test_json_failure_envelope_includes_structured_error(tmp_path: Path) -> None:
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

    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "plan.approve"
    assert payload["error"]["code"] == "WORKFLOW_REJECTION"
    assert payload["error"]["message"]
    assert payload["error"]["exit_code"] == 3
