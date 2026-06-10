# ruff: noqa: E501
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app

runner = CliRunner()


def _json_output(result) -> dict[str, object]:
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    return payload


def _init(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0, result.stdout


def _record_done(tmp_path: Path, *, title: str, slug: str) -> str:
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "task",
            "record",
            title,
            "--slug",
            slug,
            "--description",
            title,
            "--summary",
            f"Complete {title}",
            "--allow-empty-record",
            "--reason",
            "test",
        ],
    )
    payload = _json_output(result)
    task_id = payload["result"]["task_id"]
    assert isinstance(task_id, str)
    return task_id


def _create_task(tmp_path: Path, *, title: str, slug: str) -> str:
    result = runner.invoke(
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
        ],
    )
    payload = _json_output(result)
    task_id = payload["result"]["id"]
    assert isinstance(task_id, str)
    return task_id


def _archive(tmp_path: Path, ref: str) -> None:
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "archive",
            ref,
            "--reason",
            "Hide historical work",
        ],
    )
    assert result.exit_code == 0, result.stdout


# specweave: feature=specs/behavior/features/task_archive/archive.feature
# specweave: scenario=@bdd-task-archive-archive-hides-task-from-default-list
def test_archive_hides_task_from_default_list(tmp_path: Path) -> None:
    _init(tmp_path)
    task_id = _record_done(tmp_path, title="Legacy task", slug="legacy-task")
    _archive(tmp_path, task_id)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "task", "list"])
    assert result.exit_code == 0, result.stdout
    assert "legacy-task" not in result.stdout

    archived = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "list", "--archived"],
    )
    assert archived.exit_code == 0, archived.stdout
    assert "legacy-task" in archived.stdout
    assert "archived" in archived.stdout


# specweave: feature=specs/behavior/features/task_archive/archive.feature
# specweave: scenario=@bdd-task-archive-archived-slug-can-be-reused-and-archived-slug-can-be-ambiguous
def test_archived_slug_can_be_reused_and_archived_slug_can_be_ambiguous(
    tmp_path: Path,
) -> None:
    _init(tmp_path)
    first = _record_done(tmp_path, title="No log feature v1", slug="no-log-feature")
    _archive(tmp_path, first)

    second = _record_done(tmp_path, title="No log feature v2", slug="no-log-feature")
    _archive(tmp_path, second)

    archived = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "list",
            "--archived",
            "--slug",
            "no-log-feature",
        ],
    )
    assert archived.exit_code == 0, archived.stdout
    assert first in archived.stdout
    assert second in archived.stdout

    ambiguous = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "show",
            "no-log-feature",
            "--include-archived",
        ],
    )
    assert ambiguous.exit_code != 0
    assert "ambiguous" in ambiguous.output.lower()


# specweave: feature=specs/behavior/features/task_archive/archive.feature
# specweave: scenario=@bdd-task-archive-unarchive-rejects-visible-slug-conflict-and-accepts-new-slug
def test_unarchive_rejects_visible_slug_conflict_and_accepts_new_slug(
    tmp_path: Path,
) -> None:
    _init(tmp_path)
    archived_task = _record_done(tmp_path, title="Feature", slug="same-slug")
    _archive(tmp_path, archived_task)

    _create_task(tmp_path, title="New active feature", slug="same-slug")

    conflict = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "unarchive",
            archived_task,
            "--reason",
            "Need it back",
        ],
    )
    assert conflict.exit_code != 0
    assert "slug" in conflict.output.lower()

    restored = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "unarchive",
            archived_task,
            "--reason",
            "Need it back",
            "--slug",
            "same-slug-archived",
        ],
    )
    assert restored.exit_code == 0, restored.stdout


# specweave: feature=specs/behavior/features/task_archive/archive.feature
# specweave: scenario=@bdd-task-archive-archiving-all-tasks-does-not-reset-next-task-number
def test_archiving_all_tasks_does_not_reset_next_task_number(tmp_path: Path) -> None:
    _init(tmp_path)
    first = _record_done(tmp_path, title="Done one", slug="done-one")
    _archive(tmp_path, first)

    second = _create_task(tmp_path, title="Only visible now", slug="only-visible")
    assert second == "task-0002"


# specweave: feature=specs/behavior/features/task_archive/archive.feature
# specweave: scenario=@bdd-task-archive-archived-task-mutation-is-rejected-and-exact-id-still-reads
def test_archived_task_mutation_is_rejected_and_exact_id_still_reads(
    tmp_path: Path,
) -> None:
    _init(tmp_path)
    task_id = _record_done(
        tmp_path,
        title="Immutable archived",
        slug="immutable-archived",
    )
    _archive(tmp_path, task_id)

    activate = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "activate", task_id],
    )
    assert activate.exit_code != 0
    assert "Cannot activate archived task" in activate.output

    show = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "show", task_id],
    )
    assert show.exit_code == 0, show.stdout
    assert "immutable-archived" in show.stdout
