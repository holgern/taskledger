from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.frontmatter import (
    read_markdown_front_matter,
    write_markdown_front_matter,
)
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


def test_changelog_add_strict_rejects_summary_warning_without_writing(
    tmp_path: Path,
) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)

    result = runner.invoke(
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
            "Simplified task trace output to taskledger-native references only",
        ],
    )
    assert result.exit_code != 0
    assert "action phrase" in (result.stdout + result.stderr)
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
    assert not entry_path.exists()


def test_changelog_lint_human_output_lists_warning_details(tmp_path: Path) -> None:
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
                "changed",
                "--summary",
                "Changed trace output to taskledger-native references only",
            ],
        ).exit_code
        == 0
    )
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
    metadata["summary"] = (
        "Simplified task trace output to taskledger-native references only"
    )
    write_markdown_front_matter(entry_path, metadata, body)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "lint",
            "--task",
            task_id,
        ],
    )
    assert result.exit_code == 0
    assert "warning(s)" in result.stdout
    assert "WARN" in result.stdout
    assert "action phrase" in result.stdout


def test_changelog_update_changes_summary_without_import_file(tmp_path: Path) -> None:
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
                "changed",
                "--summary",
                "Changed release range rendering for build context",
            ],
        ).exit_code
        == 0
    )
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
    before_metadata, _ = read_markdown_front_matter(entry_path)
    before_created = str(before_metadata["created_at"])
    before_updated = str(before_metadata["updated_at"])

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "update",
            "cle-0001",
            "--task",
            task_id,
            "--summary",
            "Changed trace output to taskledger-native references only",
        ],
    )
    assert result.exit_code == 0, result.stdout

    after_metadata, _ = read_markdown_front_matter(entry_path)
    assert (
        after_metadata["summary"]
        == "Changed trace output to taskledger-native references only"
    )
    assert str(after_metadata["created_at"]) == before_created
    assert str(after_metadata["updated_at"]) != before_updated


def test_changelog_add_many_writes_entries_atomically(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)
    batch_file = workspace / "entries.yaml"
    batch_file.write_text(
        (
            "entries:\n"
            "  - category: changed\n"
            "    summary: Changed trace output to taskledger-native references only\n"
            "    body: First entry body.\n"
            "    audience: developer\n"
            "    scopes: [trace]\n"
            "  - category: documentation\n"
            "    summary: Documented isolated task-ledger semantics in docs and "
            "agent guidance\n"
            "    body: Second entry body.\n"
            "    audience: user\n"
            "    scopes: [docs]\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "add-many",
            "--task",
            task_id,
            "--file",
            str(batch_file),
        ],
    )
    assert result.exit_code == 0, result.stdout
    changelog_dir = (
        workspace / ".taskledger" / "ledgers" / "main" / "tasks" / task_id / "changelog"
    )
    assert (changelog_dir / "cle-0001.md").exists()
    assert (changelog_dir / "cle-0002.md").exists()
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
    assert lint_result.exit_code == 0, lint_result.stdout


def test_changelog_add_many_strict_failure_writes_nothing(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)
    batch_file = workspace / "entries.yaml"
    batch_file.write_text(
        (
            "entries:\n"
            "  - category: changed\n"
            "    summary: Changed trace output to taskledger-native references only\n"
            "  - category: changed\n"
            "    summary: Simplified task trace output to taskledger-native "
            "references only\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "add-many",
            "--task",
            task_id,
            "--file",
            str(batch_file),
        ],
    )
    assert result.exit_code != 0
    changelog_dir = (
        workspace / ".taskledger" / "ledgers" / "main" / "tasks" / task_id / "changelog"
    )
    assert not list(changelog_dir.glob("cle-*.md"))


def test_changelog_prompt_includes_strict_summary_rules_and_batch_skeleton(
    tmp_path: Path,
) -> None:
    workspace = init_workspace(tmp_path)
    task_id = create_done_task(workspace, allow_lint_errors=True)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "changelog",
            "prompt",
            "--task",
            task_id,
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "## Strict summary rules" in result.stdout
    assert "- Added" in result.stdout
    assert "- Changed" in result.stdout
    assert "- Fixed" in result.stdout
    assert "- Documented" in result.stdout
    assert "add-many" in result.stdout
    assert "entries:" in result.stdout
