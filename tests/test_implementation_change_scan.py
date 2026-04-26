from __future__ import annotations

import json
import subprocess
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


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _prepare_implementation(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "impl-scan",
                "--description",
                "Capture implementation evidence.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "impl-scan"]
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
                "impl-scan",
                "--criterion",
                "Record the implementation evidence.",
                "--text",
                "## Goal\n\nCapture implementation evidence.",
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
                "impl-scan",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Proceed.",
                "--allow-empty-todos",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "start", "impl-scan"],
        ).exit_code
        == 0
    )


def test_scan_changes_from_git_records_branch_status_and_diff_stat(
    tmp_path: Path,
) -> None:
    _prepare_implementation(tmp_path)

    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Taskledger Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    readme = tmp_path / "README.md"
    readme.write_text("hello\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    readme.write_text("hello\nworld\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "scan-changes",
            "impl-scan",
            "--from-git",
            "--summary",
            "Captured Git state.",
        ],
    )
    payload = _json(result)
    assert result.exit_code == 0
    assert payload["result"]["kind"] == "scan"
    assert "branch:" in payload["result"]["git_diff_stat"]
    assert "README.md" in payload["result"]["git_diff_stat"]


def test_scan_changes_from_git_rejects_non_git_workspace(tmp_path: Path) -> None:
    _prepare_implementation(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "scan-changes",
            "impl-scan",
            "--from-git",
        ],
    )
    payload = _json(result)
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert "Git work tree" in payload["error"]["message"]


def test_manual_implement_change_still_works_via_canonical_command(
    tmp_path: Path,
) -> None:
    _prepare_implementation(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "change",
            "impl-scan",
            "--path",
            "taskledger/services/tasks.py",
            "--kind",
            "edit",
            "--summary",
            "Manual evidence entry.",
        ],
    )
    payload = _json(result)
    assert result.exit_code == 0
    assert payload["result"]["path"] == "taskledger/services/tasks.py"
