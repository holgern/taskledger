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


def test_cli_command_tree_matches_option_b_split_contract(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    result = runner.invoke(app, ["--cwd", str(tmp_path), "--help"])

    assert result.exit_code == 0
    for name in (
        "init",
        "status",
        "board",
        "next",
        "doctor",
        "report",
        "export",
        "import",
        "snapshot",
        "search",
        "grep",
        "symbols",
        "deps",
        "item",
        "memory",
        "context",
        "repo",
        "runs",
        "validation",
        "workflow",
        "exec-request",
        "compose",
        "runtime-support",
    ):
        assert name in result.stdout

def test_workflow_group_includes_parity_commands(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    result = runner.invoke(app, ["--cwd", str(tmp_path), "workflow", "--help"])

    assert result.exit_code == 0
    for command in (
        "list",
        "save",
        "delete",
        "default",
        "set-default",
        "show",
        "assign",
        "state",
        "stages",
        "records",
        "latest",
        "transitions",
        "can-enter",
        "enter",
        "mark-running",
        "mark-succeeded",
        "mark-failed",
        "mark-needs-review",
        "approve-stage",
    ):
        assert command in result.stdout


def test_extended_cli_groups_are_registered(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])

    for command in ("exec-request", "compose", "runtime-support"):
        result = runner.invoke(app, ["--cwd", str(tmp_path), command, "--help"])
        assert result.exit_code == 0
