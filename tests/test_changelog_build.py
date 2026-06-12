from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from taskledger.cli import app
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


def _prepare_release_with_entry(workspace: Path) -> tuple[str, str]:
    boundary = create_done_task(
        workspace,
        title="Release boundary",
        slug="release-boundary",
        allow_lint_errors=True,
    )
    task_id = create_done_task(
        workspace,
        title="Build entry task",
        slug="build-entry-task",
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
                "fixed",
                "--summary",
                "Fixed deterministic changelog section rendering",
                "--release-version",
                "0.4.2",
            ],
        ).exit_code
        == 0
    )
    return boundary, task_id


def test_build_dry_run_renders_release_section(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    _, _ = _prepare_release_with_entry(workspace)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "build",
            "0.4.2",
            "--release-date",
            "2026-05-30",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "## v0.4.2 - 2026-05-30" in result.stdout
    assert "### Fixed" in result.stdout
    assert "- Fixed deterministic changelog section rendering" in result.stdout


def test_build_updates_changelog_file_after_unreleased(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    _, _ = _prepare_release_with_entry(workspace)
    changelog = workspace / "CHANGELOG.md"
    changelog.write_text(
        (
            "# Changelog\n\n## Unreleased\n\n- pending\n\n## v0.4.1 - 2026-05-01\n"
            "\n- old\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "build",
            "0.4.2",
            "--release-date",
            "2026-05-30",
            "--target-file",
            "CHANGELOG.md",
        ],
    )
    assert result.exit_code == 0, result.stdout
    updated = changelog.read_text(encoding="utf-8")
    assert updated.index("## Unreleased") < updated.index("## v0.4.2 - 2026-05-30")
    assert updated.index("## v0.4.2 - 2026-05-30") < updated.index(
        "## v0.4.1 - 2026-05-01"
    )


def test_build_replace_overwrites_existing_version_section(tmp_path: Path) -> None:
    workspace = init_workspace(tmp_path)
    _, _ = _prepare_release_with_entry(workspace)
    changelog = workspace / "CHANGELOG.md"
    changelog.write_text(
        (
            "# Changelog\n\n## v0.4.2 - 2026-05-30\n\n- stale\n\n## v0.4.1 - "
            "2026-05-01\n\n- old\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "build",
            "0.4.2",
            "--release-date",
            "2026-05-30",
            "--replace",
        ],
    )
    assert result.exit_code == 0, result.stdout
    updated = changelog.read_text(encoding="utf-8")
    assert "- stale" not in updated
    assert "- Fixed deterministic changelog section rendering" in updated


def test_build_strict_fails_when_release_has_no_accepted_entries(
    tmp_path: Path,
) -> None:
    workspace = init_workspace(tmp_path)
    boundary = create_done_task(
        workspace,
        title="Release boundary",
        slug="release-boundary",
        allow_lint_errors=True,
    )
    task_id = create_done_task(
        workspace,
        title="No changelog task",
        slug="no-changelog-task",
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

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(workspace),
            "build",
            "0.4.2",
            "--release-date",
            "2026-05-30",
        ],
    )
    assert result.exit_code != 0
