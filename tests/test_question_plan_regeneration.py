from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app


def _runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _runner()


def _json(result) -> dict[str, object]:
    return json.loads(result.stdout)


def _init_task(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "new",
                "Regeneration task",
                "--slug",
                "regen-task",
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0


def test_required_question_blocks_approval_until_answered_and_regenerated(
    tmp_path: Path,
) -> None:
    _init_task(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "add",
                "--text",
                "Which database?",
                "--required-for-plan",
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
                "--criterion",
                "Database choice is honored.",
                "--text",
                "Initial plan.",
            ],
        ).exit_code
        == 0
    )
    blocked = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--version",
            "1",
            "--actor",
            "user",
        ],
    )
    assert blocked.exit_code != 0
    assert "open planning questions" in _json(blocked)["error"]["message"]

    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "question", "answer", "q-0001", "--text", "PostgreSQL."],
        ).exit_code
        == 0
    )
    status = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "question", "status"])
    )
    assert status["result"]["plan_regeneration_needed"] is True

    plan_text = """---
acceptance_criteria:
  - text: Database choice is honored.
todos:
  - text: Implement PostgreSQL-only behavior.
---

# Plan

Use PostgreSQL only.
"""
    regenerated = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "regenerate",
                "--from-answers",
                "--text",
                plan_text,
            ],
        )
    )
    assert regenerated["result"]["plan_version"] == 2

    show = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "show", "--version", "2"],
        )
    )
    plan = show["result"]["plan"]
    assert plan["generation_reason"] == "after_questions"
    assert plan["based_on_question_ids"] == ["q-0001"]

