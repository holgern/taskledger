from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.frontmatter import read_markdown_front_matter


def _make_runner() -> CliRunner:
    runner_factory = cast(Any, CliRunner)
    try:
        return cast(CliRunner, runner_factory(mix_stderr=False))
    except TypeError:
        return cast(CliRunner, runner_factory())


runner = _make_runner()


def _json(result: Any) -> dict[str, Any]:
    assert result.exit_code == 0, result.stdout
    payload = cast(dict[str, Any], json.loads(result.stdout))
    assert payload["ok"] is True
    return payload


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _plan_text(title: str) -> str:
    return f"""---
goal: Ship {title}.
acceptance_criteria:
  - id: ac-0001
    text: "{title} works."
todos:
  - id: todo-0001
    text: "Implement {title}."
    validation_hint: "python -c \\"print('ok')\\""
---

# Plan

Ship {title}.
"""


def _create_done_task(
    tmp_path: Path,
    *,
    title: str,
    slug: str,
    labels: tuple[str, ...] = (),
) -> str:
    result = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "task",
                "create",
                title,
                "--slug",
                slug,
                "--description",
                f"{title} summary.",
            ],
        )
    )
    task_id = str(result["result"]["id"])
    if labels:
        command = ["--cwd", str(tmp_path), "task", "edit", "--task", slug]
        for label in labels:
            command.extend(["--add-label", label])
        assert runner.invoke(app, command).exit_code == 0
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "task", "activate", slug]).exit_code
        == 0
    )
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "propose", "--text", _plan_text(title)],
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
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "implement", "start"]).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "change",
                "--path",
                "taskledger/services/releases.py",
                "--kind",
                "edit",
                "--summary",
                f"Implemented {title}.",
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
                "implement",
                "command",
                "--",
                "python",
                "-c",
                "print('ok')",
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
                "todo",
                "done",
                "todo-0001",
                "--evidence",
                "python -c print('ok')",
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
                "implement",
                "finish",
                "--summary",
                f"Implemented {title}.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "validate", "start"]).exit_code == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate",
                "check",
                "--criterion",
                "ac-0001",
                "--status",
                "pass",
                "--evidence",
                "python -c print('ok')",
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
                "validate",
                "finish",
                "--result",
                "passed",
                "--summary",
                f"Validated {title}.",
            ],
        ).exit_code
        == 0
    )
    return task_id


def _create_failed_validation_task(tmp_path: Path, *, title: str, slug: str) -> str:
    result = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "task",
                "create",
                title,
                "--slug",
                slug,
                "--description",
                f"{title} summary.",
            ],
        )
    )
    task_id = str(result["result"]["id"])
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "task", "activate", slug]).exit_code
        == 0
    )
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "propose", "--text", _plan_text(title)],
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
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "implement", "start"]).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "change",
                "--path",
                "taskledger/services/releases.py",
                "--kind",
                "edit",
                "--summary",
                f"Implemented {title}.",
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
                "implement",
                "command",
                "--",
                "python",
                "-c",
                "print('ok')",
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
                "todo",
                "done",
                "todo-0001",
                "--evidence",
                "python -c print('ok')",
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
                "implement",
                "finish",
                "--summary",
                f"Implemented {title}.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "validate", "start"]).exit_code == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate",
                "check",
                "--criterion",
                "ac-0001",
                "--status",
                "fail",
                "--evidence",
                "python -c print('fail')",
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
                "validate",
                "finish",
                "--result",
                "failed",
                "--summary",
                f"Validation failed for {title}.",
            ],
        ).exit_code
        == 0
    )
    return task_id


def test_release_tag_persists_release_record(tmp_path: Path) -> None:
    _init_project(tmp_path)
    task_id = _create_done_task(
        tmp_path, title="Release boundary", slug="release-boundary"
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "release",
            "tag",
            "0.4.1",
            "--at-task",
            task_id,
            "--note",
            "0.4.1 released",
        ],
    )
    assert result.exit_code == 0, result.stdout

    path = tmp_path / ".taskledger" / "releases" / "0.4.1.md"
    metadata, _ = read_markdown_front_matter(path)
    assert metadata["object_type"] == "release"
    assert metadata["version"] == "0.4.1"
    assert metadata["boundary_task_id"] == task_id


def test_release_tag_rejects_non_done_boundary(tmp_path: Path) -> None:
    _init_project(tmp_path)
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "Not done yet",
            "--slug",
            "not-done-yet",
            "--description",
            "Still in draft.",
        ],
    )
    assert result.exit_code == 0

    tag_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "release",
            "tag",
            "0.4.1",
            "--at-task",
            "not-done-yet",
        ],
    )
    assert tag_result.exit_code != 0
    assert "done tasks" in tag_result.stdout or "done tasks" in tag_result.stderr


def test_release_tag_rejects_duplicate_version(tmp_path: Path) -> None:
    _init_project(tmp_path)
    task_id = _create_done_task(
        tmp_path, title="Release boundary", slug="release-boundary"
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "release",
                "tag",
                "0.4.1",
                "--at-task",
                task_id,
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "release",
            "tag",
            "0.4.1",
            "--at-task",
            task_id,
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in result.stdout or "already exists" in result.stderr


def test_release_list_is_sorted_by_boundary_task(tmp_path: Path) -> None:
    _init_project(tmp_path)
    first = _create_done_task(
        tmp_path, title="First release boundary", slug="first-release-boundary"
    )
    second = _create_done_task(
        tmp_path, title="Second release boundary", slug="second-release-boundary"
    )

    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "release", "tag", "0.4.2", "--at-task", second],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "release", "tag", "0.4.1", "--at-task", first],
        ).exit_code
        == 0
    )

    result = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "release", "list"])
    )
    versions = [item["version"] for item in result["result"]["releases"]]
    assert versions == ["0.4.1", "0.4.2"]


def test_release_show_returns_persisted_record(tmp_path: Path) -> None:
    _init_project(tmp_path)
    task_id = _create_done_task(
        tmp_path, title="Release boundary", slug="release-boundary"
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "release",
                "tag",
                "0.4.1",
                "--at-task",
                task_id,
                "--note",
                "0.4.1 released",
            ],
        ).exit_code
        == 0
    )

    result = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "release", "show", "0.4.1"],
        )
    )
    release = result["result"]["release"]
    assert release["version"] == "0.4.1"
    assert release["boundary_task_id"] == task_id
    assert release["note"] == "0.4.1 released"


def test_release_changelog_filters_done_tasks_and_reports_omitted(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    boundary = _create_done_task(
        tmp_path, title="Release boundary", slug="release-boundary"
    )
    done_one = _create_done_task(
        tmp_path,
        title="Improve dashboard refresh stability",
        slug="dashboard-refresh-stability",
        labels=("ui", "serve"),
    )
    failed = _create_failed_validation_task(
        tmp_path,
        title="Dashboard polish",
        slug="dashboard-polish",
    )
    done_two = _create_done_task(
        tmp_path,
        title="Improve changelog rendering",
        slug="improve-changelog-rendering",
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "release", "tag", "0.4.1", "--at-task", boundary],
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
                "release",
                "changelog",
                "0.4.2",
                "--since",
                "0.4.1",
                "--until-task",
                done_two,
            ],
        )
    )
    payload = result["result"]
    assert payload["kind"] == "release_changelog_context"
    assert [item["task_id"] for item in payload["tasks"]] == [done_one, done_two]
    assert payload["omitted_task_count"] == 1
    assert payload["omitted_tasks"][0]["task_id"] == failed
    assert payload["omitted_tasks"][0]["status_stage"] == "failed_validation"


def test_release_changelog_markdown_includes_instruction_and_evidence(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    boundary = _create_done_task(
        tmp_path, title="Release boundary", slug="release-boundary"
    )
    included = _create_done_task(
        tmp_path,
        title="Improve dashboard refresh stability",
        slug="dashboard-refresh-stability",
        labels=("ui", "serve"),
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "release", "tag", "0.4.1", "--at-task", boundary],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "release",
            "changelog",
            "0.4.2",
            "--since",
            "0.4.1",
            "--until-task",
            included,
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "# Changelog source for taskledger 0.4.2" in result.stdout
    assert "## LLM instruction" in result.stdout
    assert "Improve dashboard refresh stability" in result.stdout
    assert "Implementation summary:" in result.stdout
    assert "Relevant changes:" in result.stdout
    assert "Evidence:" in result.stdout
    assert "python -c print('ok')" in result.stdout


def test_release_changelog_supports_bootstrap_since_task(tmp_path: Path) -> None:
    _init_project(tmp_path)
    boundary = _create_done_task(
        tmp_path, title="Release boundary", slug="release-boundary"
    )
    included = _create_done_task(
        tmp_path,
        title="Improve changelog rendering",
        slug="improve-changelog-rendering",
    )

    result = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "release",
                "changelog",
                "0.4.2",
                "--since-task",
                boundary,
                "--until-task",
                included,
            ],
        )
    )
    payload = result["result"]
    assert payload["since_version"] is None
    assert payload["since_task_id"] == boundary
    assert payload["tasks"][0]["task_id"] == included
