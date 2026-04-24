from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def test_cli_command_tree_matches_task_first_contract(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    result = runner.invoke(app, ["--cwd", str(tmp_path), "--help"])

    assert result.exit_code == 0
    for name in (
        "init",
        "status",
        "doctor",
        "export",
        "import",
        "snapshot",
        "search",
        "grep",
        "symbols",
        "deps",
        "task",
        "plan",
        "question",
        "implement",
        "validate",
        "todo",
        "intro",
        "file",
        "require",
        "lock",
        "handoff",
        "next-action",
        "can",
        "reindex",
    ):
        assert name in result.stdout


def test_legacy_cli_groups_are_removed(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])

    for command in (
        "board",
        "next",
        "report",
        "item",
        "memory",
        "context",
        "repo",
        "runs",
        "run",
        "validation",
        "workflow",
        "exec-request",
        "compose",
        "runtime-support",
    ):
        result = runner.invoke(app, ["--cwd", str(tmp_path), command, "--help"])
        assert result.exit_code != 0


def test_task_first_subcommands_are_registered(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])

    expected = {
        "task": ("create", "list", "show", "edit", "cancel", "close"),
        "plan": (
            "start",
            "propose",
            "list",
            "show",
            "diff",
            "approve",
            "reject",
            "revise",
        ),
        "question": ("add", "list", "open", "answer", "dismiss"),
        "implement": (
            "start",
            "log",
            "deviation",
            "artifact",
            "add-change",
            "show",
            "finish",
        ),
        "validate": ("start", "add-check", "show", "finish"),
        "todo": ("add", "list", "show", "done", "undone"),
        "file": ("link", "unlink", "list"),
        "require": ("add", "list", "remove"),
        "lock": ("show", "break", "list"),
        "handoff": (
            "show",
            "plan-context",
            "implementation-context",
            "validation-context",
        ),
    }

    for command, subcommands in expected.items():
        result = runner.invoke(app, ["--cwd", str(tmp_path), command, "--help"])
        assert result.exit_code == 0
        for subcommand in subcommands:
            assert subcommand in result.stdout
