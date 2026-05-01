from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.indexes import rebuild_v2_indexes
from taskledger.storage.task_store import ensure_v2_layout, resolve_v2_paths


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _json(result) -> dict[str, object]:
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _removed_index_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    indexes_dir = tmp_path / ".taskledger" / "ledgers" / "main" / "indexes"
    return (
        indexes_dir / "tasks.json",
        indexes_dir / "plan_versions.json",
        indexes_dir / "latest_runs.json",
    )


def _prepare_task_with_plan(
    tmp_path: Path,
    *,
    slug: str,
    approve: bool = False,
    start_implementation: bool = False,
) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                slug,
                "--description",
                "Exercise canonical plan and run scans.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(tmp_path), "task", "activate", slug]).exit_code
        == 0
    )
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0
    plan_text = """---
goal: Verify canonical plan and run scans.
acceptance_criteria:
  - id: ac-0001
    text: Canonical records drive task commands.
todos:
  - id: todo-0001
    text: Exercise canonical read paths.
---

# Plan

Use task bundles instead of derived task, plan, and run indexes.
"""
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "propose", "--text", plan_text],
        ).exit_code
        == 0
    )
    if not approve and not start_implementation:
        return
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
                "Ready to implement.",
            ],
        ).exit_code
        == 0
    )
    if start_implementation:
        assert (
            runner.invoke(
                app,
                ["--cwd", str(tmp_path), "implement", "start"],
            ).exit_code
            == 0
        )


def test_task_create_uses_task_bundle_layout(tmp_path: Path) -> None:
    _init_project(tmp_path)

    project_dir = tmp_path / ".taskledger" / "ledgers" / "main"
    assert (project_dir / "intros").is_dir()
    assert (project_dir / "releases").is_dir()
    assert (project_dir / "tasks").is_dir()
    assert (project_dir / "events").is_dir()
    assert (project_dir / "indexes").is_dir()
    for legacy_name in (
        "items",
        "memories",
        "contexts",
        "stages",
        "workflows",
    ):
        assert not (project_dir / legacy_name).exists()

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "bundle-layout",
            "--description",
            "Verify the bundle layout.",
        ],
    )
    assert result.exit_code == 0, result.stdout

    task_dir = project_dir / "tasks" / "task-0001"
    assert (task_dir / "task.md").is_file()
    assert (task_dir / "todos").is_dir()
    assert (task_dir / "links").is_dir()
    assert (task_dir / "requirements").is_dir()
    assert not (task_dir / "todos.yaml").exists()
    assert not (task_dir / "links.yaml").exists()
    assert not (task_dir / "requirements.yaml").exists()
    assert (task_dir / "plans").is_dir()
    assert (task_dir / "questions").is_dir()
    assert (task_dir / "runs").is_dir()
    assert (task_dir / "changes").is_dir()
    assert (task_dir / "artifacts").is_dir()
    assert (task_dir / "audit").is_dir()

    # Empty collections should produce no per-record files
    assert list((task_dir / "todos").glob("todo-*.md")) == []
    assert list((task_dir / "links").glob("link-*.md")) == []
    assert list((task_dir / "requirements").glob("req-*.md")) == []


def test_task_list_scans_task_markdown_without_indexes(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "scan-layout",
            "--description",
            "Listing should scan task bundles.",
        ],
    )

    indexes_dir = tmp_path / ".taskledger" / "indexes"
    for path in indexes_dir.glob("*.json"):
        path.unlink()

    result = runner.invoke(app, ["--cwd", str(tmp_path), "task", "list"])
    assert result.exit_code == 0, result.stdout
    assert "scan-layout" in result.stdout


def test_task_list_ignores_removed_legacy_indexes(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "legacy-indexes",
                "--description",
                "Listing should ignore legacy removed indexes.",
            ],
        ).exit_code
        == 0
    )
    for path in _removed_index_paths(tmp_path):
        path.write_text("{not valid json", encoding="utf-8")

    result = runner.invoke(app, ["--cwd", str(tmp_path), "task", "list"])
    assert result.exit_code == 0, result.stdout
    assert "legacy-indexes" in result.stdout


def test_ensure_v2_layout_does_not_create_removed_indexes(tmp_path: Path) -> None:
    ensure_v2_layout(tmp_path)
    for path in _removed_index_paths(tmp_path):
        assert not path.exists()


def test_plan_list_does_not_need_removed_indexes(tmp_path: Path) -> None:
    _prepare_task_with_plan(tmp_path, slug="plan-scan")
    for path in _removed_index_paths(tmp_path):
        path.unlink(missing_ok=True)

    payload = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "plan", "list"])
    )
    assert payload["result"]["plans"][0]["plan_version"] == 1


def test_implement_status_does_not_need_removed_indexes(tmp_path: Path) -> None:
    _prepare_task_with_plan(
        tmp_path,
        slug="run-scan",
        approve=True,
        start_implementation=True,
    )
    for path in _removed_index_paths(tmp_path):
        path.unlink(missing_ok=True)

    payload = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "implement", "status"])
    )
    assert payload["result"]["task_id"] == "task-0001"
    assert payload["result"]["total"] == 1
    assert payload["result"]["done"] == 0


def test_reindex_does_not_create_removed_indexes(tmp_path: Path) -> None:
    ensure_v2_layout(tmp_path)
    paths = resolve_v2_paths(tmp_path)

    rebuild_v2_indexes(paths)

    for path in _removed_index_paths(tmp_path):
        assert not path.exists()


def test_task_create_no_orphan_slug_directory(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "slug-orphan-check",
            "--description",
            "No empty slug dir should appear.",
        ],
    )
    assert result.exit_code == 0, result.stdout

    tasks_dir = tmp_path / ".taskledger" / "ledgers" / "main" / "tasks"
    child_names = [p.name for p in tasks_dir.iterdir()]
    # Only the canonical task-NNNN directory should exist
    assert child_names == ["task-0001"], f"unexpected directories: {child_names}"
    assert not (tasks_dir / "slug-orphan-check").exists()


def test_repair_task_dirs_removes_orphans(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "orphan-parent",
            "--description",
            "Create a task then add an orphan dir.",
        ],
    )
    assert result.exit_code == 0, result.stdout

    tasks_dir = tmp_path / ".taskledger" / "ledgers" / "main" / "tasks"
    # Manually create an empty slug-like directory
    (tasks_dir / "orphan-parent").mkdir()
    assert (tasks_dir / "orphan-parent").exists()

    result = runner.invoke(app, ["--cwd", str(tmp_path), "repair", "task-dirs"])
    assert result.exit_code == 0, result.stdout
    assert "1" in result.stdout
    assert not (tasks_dir / "orphan-parent").exists()
