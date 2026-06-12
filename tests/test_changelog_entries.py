from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.frontmatter import read_markdown_front_matter
from tests.support.builders import create_done_task, init_workspace

pytestmark = [pytest.mark.cli, pytest.mark.integration, pytest.mark.slow]


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _json(result: Any) -> dict[str, Any]:
    assert result.exit_code == 0, result.stdout
    payload = cast(dict[str, Any], json.loads(result.stdout))
    assert payload["ok"] is True
    return payload


def test_changelog_add_writes_task_local_markdown_file(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "add",
            "--category",
            "fixed",
            "--summary",
            "Fixed changelog rendering for grouped sections",
        ],
    )
    assert result.exit_code == 0, result.stdout

    entry_path = (
        workspace
        / ".taskledger"
        / "ledgers"
        / "main"
        / "tasks"
        / task_id
        / "changelog"
        / "cle-0001.md"
    )
    metadata, body = read_markdown_front_matter(entry_path)
    assert metadata["object_type"] == "changelog_entry"
    assert metadata["task_id"] == task_id
    assert metadata["entry_id"] == "cle-0001"
    assert metadata["category"] == "fixed"
    assert metadata["status"] == "accepted"
    assert metadata["summary"] == "Fixed changelog rendering for grouped sections"
    assert body.strip() == ""


def test_changelog_list_by_version_uses_release_scope(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    boundary = create_done_task(
        workspace,
        title="Release boundary",
        slug="release-boundary",
        allow_lint_errors=True,
    )
    task_id = create_done_task(
        workspace,
        title="Entry task",
        slug="entry-task",
        allow_lint_errors=True,
    )

    assert (
        runner.invoke(
            app,
            ["--cwd", str(workspace), "release", "tag", "0.4.1", "--at-task", boundary],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(workspace), "release", "tag", "0.4.2", "--at-task", task_id],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(workspace),
                "changelog",
                "add",
                "--task",
                task_id,
                "--category",
                "changed",
                "--summary",
                "Changed release range rendering for build context",
            ],
        ).exit_code
        == 0
    )

    payload = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(workspace),
                "--json",
                "changelog",
                "list",
                "--version",
                "0.4.2",
            ],
        )
    )
    entries = payload["result"]["entries"]
    assert len(entries) == 1
    assert entries[0]["task_id"] == task_id
    assert entries[0]["entry_id"] == "cle-0001"


def test_changelog_lint_strict_fails_for_invalid_entry_file(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)
    entry_path = (
        workspace
        / ".taskledger"
        / "ledgers"
        / "main"
        / "tasks"
        / task_id
        / "changelog"
        / "cle-9999.md"
    )
    entry_path.parent.mkdir(parents=True, exist_ok=True)
    entry_path.write_text(
        "---\n"
        "schema_version: 1\n"
        "object_type: changelog_entry\n"
        "file_version: '0.1.0'\n"
        "entry_id: cle-9999\n"
        "task_id: task-9999\n"
        "category: fixed\n"
        "status: accepted\n"
        "---\n\n"
        "Broken\n",
        encoding="utf-8",
    )

    lint_result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "lint",
            "--task",
            task_id,
            "--strict",
        ],
    )
    assert lint_result.exit_code != 0


def test_changelog_prompt_includes_validation_and_existing_entries(
    tmp_path: Path,
) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(workspace),
                "changelog",
                "add",
                "--task",
                task_id,
                "--category",
                "added",
                "--summary",
                "Added deterministic changelog sidecar generation",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        ["--cwd", str(workspace), "changelog", "prompt", "--task", task_id],
    )
    assert result.exit_code == 0
    assert "## Validation checks and evidence" in result.stdout
    assert "## Existing changelog entries" in result.stdout
    assert "cle-0001 [accepted] added" in result.stdout
