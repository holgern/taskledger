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
    payload = json.loads(result.stdout)
    return payload


def _prepare_proposed_plan(
    tmp_path: Path, *, criterion: str | None = "Must be explicit."
) -> None:
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "approval-task",
                "--description",
                "Exercise plan approval.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "approval-task"],
        ).exit_code
        == 0
    )
    command = [
        "--cwd",
        str(tmp_path),
        "plan",
        "propose",
        "--task",
        "approval-task",
        "--text",
        "## Goal\n\nShip safely.",
    ]
    if criterion is not None:
        command.extend(["--criterion", criterion])
    assert runner.invoke(app, command).exit_code == 0


def test_plan_approval_records_actor_metadata_and_criteria_ids(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan(tmp_path)

    approve = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "approval-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "Reviewed and approved.",
            "--allow-empty-todos",
            "--reason",
            "test",
        ],
    )
    assert approve.exit_code == 0

    show = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "show",
                "--task",
                "approval-task",
                "--version",
                "1",
            ],
        )
    )
    plan = show["result"]["plan"]
    assert plan["criteria"][0]["id"] == "ac-0001"
    assert plan["approved_by"]["actor_type"] == "user"
    assert plan["approval_note"] == "Reviewed and approved."
    assert plan["approved_at"]


def test_plan_approval_rejects_agent_approval_without_escape_hatch(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan(tmp_path)

    approve = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "approval-task",
            "--version",
            "1",
            "--actor",
            "agent",
            "--note",
            "Auto-approved.",
            "--allow-empty-todos",
            "--reason",
            "test",
        ],
    )
    payload = _json(approve)
    assert approve.exit_code != 0
    assert payload["ok"] is False
    assert "allow-agent-approval" in payload["error"]["message"]


def test_plan_approval_requires_criteria_by_default(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _prepare_proposed_plan(tmp_path, criterion=None)

    approve = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "approval-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "Reviewed and approved.",
            "--allow-empty-todos",
            "--reason",
            "test",
        ],
    )
    payload = _json(approve)
    assert approve.exit_code != 0
    assert payload["ok"] is False
    assert "acceptance criterion" in payload["error"]["message"]


def test_plan_approve_default_actor_is_agent(tmp_path: Path) -> None:
    """Verify that plan approve defaults to agent,
    requiring explicit --actor user for user approval."""
    _init_project(tmp_path)
    _prepare_proposed_plan(tmp_path)

    approve = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "approval-task",
            "--version",
            "1",
            "--note",
            "Auto-approved without specifying actor.",
            "--allow-empty-todos",
            "--reason",
            "test",
        ],
    )
    payload = _json(approve)
    assert approve.exit_code != 0
    assert payload["ok"] is False
    assert "allow-agent-approval" in payload["error"]["message"]


def test_plan_yaml_single_key_shorthand_criteria(tmp_path: Path) -> None:
    """Verify plan YAML accepts single-key shorthand mappings for criteria."""
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "shorthand-task",
                "--description",
                "Test shorthand.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "shorthand-task"],
        ).exit_code
        == 0
    )

    plan_text = """---
acceptance_criteria:
  - ac-0001: The feature works correctly.
  - id: ac-0002
    text: Edge cases handled.
---\n\n# Plan\n\nDo the work."""
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "propose",
                "--task",
                "shorthand-task",
                "--text",
                plan_text,
            ],
        ).exit_code
        == 0
    )

    show = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "show",
            "--task",
            "shorthand-task",
            "--version",
            "1",
        ],
    )
    assert show.exit_code == 0
    plan = json.loads(show.stdout)["result"]["plan"]
    assert len(plan["criteria"]) == 2
    assert plan["criteria"][0]["id"] == "ac-0001"
    assert plan["criteria"][0]["text"] == "The feature works correctly."
    assert plan["criteria"][1]["id"] == "ac-0002"
    assert plan["criteria"][1]["text"] == "Edge cases handled."
