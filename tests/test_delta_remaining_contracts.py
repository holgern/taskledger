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


def _json(result) -> dict[str, object]:
    return json.loads(result.stdout)


def _init(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _prepare_validating_task(tmp_path: Path) -> None:
    _init(tmp_path)
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "validation-gate",
            "--description",
            "Exercise validation gates.",
        ],
    ).exit_code == 0
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "validation-gate"]).exit_code == 0
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "propose",
            "validation-gate",
            "--criterion",
            "Mandatory behavior is checked.",
            "--text",
            "## Goal\n\nValidate objectively.",
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "approve",
            "validation-gate",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "Approved.",
        ],
    ).exit_code == 0
    assert runner.invoke(app, ["--cwd", str(tmp_path), "implement", "start", "validation-gate"]).exit_code == 0
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "implement",
            "finish",
            "validation-gate",
            "--summary",
            "Implemented.",
        ],
    ).exit_code == 0
    assert runner.invoke(app, ["--cwd", str(tmp_path), "validate", "start", "validation-gate"]).exit_code == 0


def test_validation_pass_requires_mandatory_criteria_checks(tmp_path: Path) -> None:
    _prepare_validating_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate",
            "finish",
            "validation-gate",
            "--result",
            "passed",
            "--summary",
            "No checks recorded.",
        ],
    )

    payload = _json(result)
    assert result.exit_code == 7
    assert payload["error"]["code"] == "VALIDATION_INCOMPLETE"
    assert payload["error"]["details"]["missing_criteria"] == ["ac-0001"]


def test_validation_pass_accepts_canonical_criterion_check(tmp_path: Path) -> None:
    _prepare_validating_task(tmp_path)
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "validate",
            "check",
            "validation-gate",
            "--criterion",
            "ac-0001",
            "--status",
            "pass",
            "--evidence",
            "pytest -q",
        ],
    ).exit_code == 0

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validate",
            "finish",
            "validation-gate",
            "--result",
            "passed",
            "--summary",
            "All gates passed.",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert _json(result)["result"]["status"] == "done"


def test_context_dossier_and_link_alias_are_canonical(tmp_path: Path) -> None:
    _init(tmp_path)
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "context-task",
            "--description",
            "Render context.",
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "link",
            "add",
            "context-task",
            "--path",
            "README.md",
            "--kind",
            "doc",
        ],
    ).exit_code == 0

    context = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "context",
            "context-task",
            "--for",
            "planning",
            "--format",
            "markdown",
        ],
    )
    assert context.exit_code == 0
    assert "Planning Context" in context.stdout
    assert "@README.md" in context.stdout

    dossier = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "dossier",
            "context-task",
            "--format",
            "markdown",
        ],
    )
    assert dossier.exit_code == 0
    assert "Task Dossier" in dossier.stdout


def test_user_dependency_waiver_unblocks_implementation(tmp_path: Path) -> None:
    _init(tmp_path)
    for slug in ("dependency", "main-task"):
        assert runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                slug,
                "--description",
                slug,
            ],
        ).exit_code == 0
    assert runner.invoke(app, ["--cwd", str(tmp_path), "require", "add", "main-task", "dependency"]).exit_code == 0
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "main-task"]).exit_code == 0
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "propose",
            "main-task",
            "--criterion",
            "Implementation starts.",
            "--text",
            "## Goal\n\nStart implementation.",
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "approve",
            "main-task",
            "--version",
            "1",
            "--actor",
            "user",
            "--note",
            "Approved.",
        ],
    ).exit_code == 0

    blocked = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "implement", "start", "main-task"],
    )
    assert blocked.exit_code == 3

    assert runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "require",
            "waive",
            "main-task",
            "dependency",
            "--actor",
            "user",
            "--reason",
            "Safe to proceed.",
        ],
    ).exit_code == 0
    allowed = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "implement", "start", "main-task"],
    )
    assert allowed.exit_code == 0, allowed.stdout
