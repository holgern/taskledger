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
                "create",
                "Regeneration task",
                "--slug",
                "regen-task",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "regen-task"],
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
            [
                "--cwd",
                str(tmp_path),
                "question",
                "answer",
                "q-0001",
                "--text",
                "PostgreSQL.",
            ],
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

    status = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "question", "status"])
    )
    assert status["result"]["plan_regeneration_needed"] is False


def test_answered_question_blocks_approval_of_stale_plan(tmp_path: Path) -> None:
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
                "SQLite.",
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

    assert blocked.exit_code == 3
    payload = json.loads(blocked.stdout)
    assert payload["error"]["code"] == "APPROVAL_REQUIRED"
    assert "Regenerate the plan from answers" in payload["error"]["message"]


def test_changed_answer_requires_regeneration_again(tmp_path: Path) -> None:
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
                "question",
                "answer",
                "q-0001",
                "--text",
                "SQLite.",
            ],
        ).exit_code
        == 0
    )
    plan_text = """---
acceptance_criteria:
  - text: Database choice is honored.
---

# Plan

Use SQLite.
"""
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "regenerate",
                "--from-answers",
                "--text",
                plan_text,
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
                "PostgreSQL.",
            ],
        ).exit_code
        == 0
    )

    status = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "question", "status"])
    )

    assert status["result"]["answered_since_latest_plan"] == ["q-0001"]
    assert status["result"]["plan_regeneration_needed"] is True


def test_answer_many_records_harness_answers_and_requires_regeneration(
    tmp_path: Path,
) -> None:
    _init_task(tmp_path)
    for text in ("Which database?", "Which cache?"):
        assert (
            runner.invoke(
                app,
                [
                    "--cwd",
                    str(tmp_path),
                    "question",
                    "add",
                    "--text",
                    text,
                    "--required-for-plan",
                ],
            ).exit_code
            == 0
        )

    result = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "question",
                "answer-many",
                "--text",
                "answers:\n  q-0001: PostgreSQL.\n  q-0002: Redis.\n",
            ],
        )
    )

    assert result["result"]["answered_question_ids"] == ["q-0001", "q-0002"]
    assert result["result"]["required_open"] == 0
    assert result["result"]["plan_regeneration_needed"] is True
    assert result["result"]["next_action"] == (
        "taskledger plan upsert --from-answers --file plan.md"
    )


def test_answer_many_rejects_duplicate_plain_text_ids(tmp_path: Path) -> None:
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

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "question",
            "answer-many",
            "--text",
            "q-0001: PostgreSQL.\nq-0001: SQLite.\n",
        ],
    )

    assert result.exit_code != 0
    assert "Duplicate key" in _json(result)["error"]["message"]


def test_plan_upsert_from_answers_releases_planning_lock_and_allows_accept(
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
                "question",
                "answer-many",
                "--text",
                "q-0001: PostgreSQL.",
            ],
        ).exit_code
        == 0
    )
    plan_text = """---
acceptance_criteria:
  - text: Database choice is honored.
todos:
  - text: Implement PostgreSQL behavior.
---

# Plan

Use PostgreSQL.
"""

    upserted = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "upsert",
                "--from-answers",
                "--text",
                plan_text,
            ],
        )
    )

    assert upserted["result"]["operation"] == "regenerated"
    assert upserted["result"]["plan_version"] == 1
    next_action = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "next-action"])
    )
    assert next_action["result"]["action"] == "plan-approve"

    accepted = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "accept",
            "--version",
            "1",
            "--note",
            "Ready.",
            "--allow-lint-errors",
        ],
    )

    assert accepted.exit_code == 0
    assert _json(accepted)["result"]["status_stage"] == "approved"


def test_next_action_prefers_question_answer_while_planning_questions_are_open(
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

    payload = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "next-action"])
    )

    result = payload["result"]
    assert result["action"] == "question-answer"
    assert result["next_command"] == 'taskledger question answer q-0001 --text "..."'
    assert result["blocking"][0]["kind"] == "open_questions"
    assert result["next_item"] == {
        "kind": "question",
        "id": "q-0001",
        "text": "Which database?",
        "status": "open",
        "required_for_plan": True,
        "plan_version": None,
    }
    assert result["commands"][0] == {
        "kind": "answer",
        "label": "Answer required question",
        "command": 'taskledger question answer q-0001 --text "..."',
        "primary": True,
    }
    assert result["progress"]["questions"] == {
        "required_open": 1,
        "required_open_ids": ["q-0001"],
    }
    assert set(result) >= {
        "kind",
        "task_id",
        "status_stage",
        "active_stage",
        "action",
        "reason",
        "blocking",
        "next_command",
        "next_item",
        "commands",
        "progress",
    }


def test_next_action_prefers_regenerate_over_approve_for_stale_answers(
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
                "SQLite.",
            ],
        ).exit_code
        == 0
    )

    payload = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "next-action"])
    )

    result = payload["result"]
    assert result["action"] == "plan-regenerate"
    assert result["next_command"] == (
        "taskledger plan upsert --from-answers --file plan.md"
    )
    assert result["blocking"][0]["kind"] == "stale_answers"
    assert result["next_item"] == {
        "kind": "answered_question",
        "id": "q-0001",
        "text": "Which database?",
        "status": "answered",
        "answer": "SQLite.",
        "answered_at": result["next_item"]["answered_at"],
        "required_for_plan": True,
        "plan_version": None,
    }
    assert result["commands"][0] == {
        "kind": "regenerate",
        "label": "Regenerate plan from answers",
        "command": "taskledger plan upsert --from-answers --file plan.md",
        "primary": True,
    }
    assert result["progress"]["questions"] == {
        "required_open": 0,
        "required_open_ids": [],
        "answered_since_latest_plan": ["q-0001"],
    }
