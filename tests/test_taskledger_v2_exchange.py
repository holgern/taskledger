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


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _json(result) -> dict[str, object]:
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    return payload


def test_export_and_import_include_v2_state(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "task",
                "create",
                "migrate-v2",
                "--description",
                "Migrate taskledger to v2.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "plan", "start", "--task", "migrate-v2"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "plan",
                "propose",
                "--task",
                "migrate-v2",
                "--text",
                "## Goal\n\nShip export support.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "handoff",
                "create",
                "--task",
                "migrate-v2",
                "--mode",
                "implementation",
                "--summary",
                "Continue elsewhere.",
            ],
        ).exit_code
        == 0
    )

    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "--json", "export"],
    )
    export_payload = _json(export_result)
    assert export_payload["result"]["v2"]["tasks"][0]["slug"] == "migrate-v2"
    assert (
        export_payload["result"]["v2"]["handoffs"][0]["summary"]
        == "Continue elsewhere."
    )
    export_file = tmp_path / "export.json"
    export_file.write_text(export_result.stdout, encoding="utf-8")

    import_result = runner.invoke(
        app,
        [
            "--cwd",
            str(dest_root),
            "import",
            str(export_file),
            "--replace",
        ],
    )
    assert import_result.exit_code == 0

    show_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "--json", "task", "show", "--task", "migrate-v2"],
    )
    task_payload = _json(show_result)
    assert task_payload["result"]["task"]["latest_plan_version"] == 1
    handoffs = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(dest_root),
                "--json",
                "handoff",
                "list",
                "--task",
                "migrate-v2",
            ],
        )
    )
    assert handoffs["result"]["handoffs"][0]["mode"] == "implementation"


def test_export_and_import_include_release_records(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "task",
                "create",
                "release-boundary",
                "--description",
                "Create a release boundary task.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(source_root), "task", "activate", "release-boundary"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(source_root), "plan", "start"]).exit_code == 0
    )
    plan_text = """---
goal: Finish a release boundary task.
acceptance_criteria:
  - id: ac-0001
    text: Release boundary task is done.
todos:
  - id: todo-0001
    text: Finish the boundary task.
    validation_hint: python -c "print('ok')"
---

# Plan

Finish the boundary task.
"""
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "plan", "propose", "--text", plan_text],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
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
        runner.invoke(
            app,
            ["--cwd", str(source_root), "implement", "start"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "implement",
                "change",
                "--path",
                "taskledger/exchange.py",
                "--kind",
                "edit",
                "--summary",
                "Prepared exchange release coverage.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
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
                str(source_root),
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
                str(source_root),
                "implement",
                "finish",
                "--summary",
                "Implemented release boundary.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "validate", "start"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
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
                str(source_root),
                "validate",
                "finish",
                "--result",
                "passed",
                "--summary",
                "Validated release boundary.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "release",
                "tag",
                "0.4.1",
                "--at-task",
                "release-boundary",
                "--note",
                "0.4.1 released",
            ],
        ).exit_code
        == 0
    )

    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "--json", "export"],
    )
    export_payload = _json(export_result)
    assert export_payload["result"]["v2"]["releases"][0]["version"] == "0.4.1"
    export_file = tmp_path / "release-export.json"
    export_file.write_text(export_result.stdout, encoding="utf-8")

    import_result = runner.invoke(
        app,
        [
            "--cwd",
            str(dest_root),
            "import",
            str(export_file),
            "--replace",
        ],
    )
    assert import_result.exit_code == 0

    show_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "--json", "release", "show", "0.4.1"],
    )
    payload = _json(show_result)
    assert payload["result"]["release"]["boundary_task_id"] == "task-0001"
