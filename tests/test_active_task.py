from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.api.tasks import activate_task, create_task, deactivate_task
from taskledger.cli import app
from taskledger.errors import NoActiveTask
from taskledger.storage.v2 import load_active_task_state, resolve_active_task


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _create_task(tmp_path: Path, slug: str = "active-flow") -> None:
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            slug,
            "--description",
            f"Task {slug}.",
        ],
    )
    assert result.exit_code == 0, result.stdout


def _json(result) -> dict[str, object]:
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    return payload


def test_active_task_state_round_trips(tmp_path: Path) -> None:
    create_task(tmp_path, title="Active", description="desc", slug="active")

    activated = activate_task(tmp_path, "active", reason="work")
    assert activated["task_id"] == "task-0001"
    assert load_active_task_state(tmp_path).task_id == "task-0001"  # type: ignore[union-attr]
    assert resolve_active_task(tmp_path).slug == "active"

    cleared = deactivate_task(tmp_path, reason="done")
    assert cleared["active"] is False
    assert load_active_task_state(tmp_path) is None
    try:
        resolve_active_task(tmp_path)
    except NoActiveTask:
        pass
    else:
        raise AssertionError("resolve_active_task should require an active task")


def test_task_scoped_command_without_active_task_fails_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "plan", "start"],
    )
    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "NO_ACTIVE_TASK"


def test_single_task_without_active_task_fails_for_task_scoped_defaults(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    _create_task(tmp_path, "only-task")

    commands = [
        ["plan", "start"],
        ["implement", "start"],
        ["validate", "start"],
        ["todo", "add", "--text", "write tests"],
        ["question", "add", "--text", "Question?"],
        ["task", "dossier"],
        ["context"],
    ]

    for command in commands:
        result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", *command])
        assert result.exit_code == 5, command
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "NO_ACTIVE_TASK"


def test_single_task_without_active_task_can_still_be_used_explicitly(
    tmp_path: Path,
) -> None:
    _init_project(tmp_path)
    _create_task(tmp_path, "only-task")

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "plan", "start", "--task", "only-task"],
    )

    assert result.exit_code == 0, result.stdout


def test_task_activate_sets_active_task(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _create_task(tmp_path, "one")

    result = runner.invoke(app, ["--cwd", str(tmp_path), "task", "activate", "one"])
    assert result.exit_code == 0, result.stdout

    payload = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "task", "active"])
    )
    assert payload["result"]["task_id"] == "task-0001"


def test_no_ref_plan_implementation_validation_flow(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _create_task(tmp_path)
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "task", "activate", "active-flow"]
        ).exit_code
        == 0
    )

    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan", "propose", "--criterion",
                "It works.",
                "--text",
                "Plan body",
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
                "plan", "approve", "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
                "--allow-empty-todos",
                "--reason",
                "test",
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
            ["--cwd", str(tmp_path), "implement", "log", "--message", "changed"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "finish", "--summary", "done"],
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
                "validate", "check", "--criterion",
                "ac-0001",
                "--status",
                "pass",
                "--evidence",
                "pytest -q",
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
                "validate", "finish", "--result",
                "passed",
                "--summary",
                "ok",
            ],
        ).exit_code
        == 0
    )


def test_secondary_positional_commands_default_to_active_task(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _create_task(tmp_path)
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "task", "activate", "active-flow"]
        ).exit_code
        == 0
    )

    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "todo", "add", "--text", "write test"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "todo", "done", "todo-0001"]
        ).exit_code
        == 0
    )

    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "question", "add", "--text", "Question?"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "answer",
                "q-0001",
                "--text",
                "Answer.",
            ],
        ).exit_code
        == 0
    )


def test_task_option_overrides_active_task(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _create_task(tmp_path, "task-a")
    _create_task(tmp_path, "task-b")
    activate = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "activate", "task-a"],
    )
    assert activate.exit_code == 0

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "plan", "start", "--task", "task-b"],
    )
    payload = _json(result)
    assert payload["result"]["task_id"] == "task-0002"


def test_export_import_preserves_active_task(tmp_path: Path) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    _init_project(source)
    _init_project(dest)
    _create_task(source, "portable")
    activate = runner.invoke(
        app,
        ["--cwd", str(source), "task", "activate", "portable"],
    )
    assert activate.exit_code == 0

    export_result = runner.invoke(app, ["--cwd", str(source), "--json", "export"])
    export_payload = _json(export_result)
    assert export_payload["result"]["v2"]["active_task"]["task_id"] == "task-0001"
    export_file = tmp_path / "export.json"
    export_file.write_text(export_result.stdout, encoding="utf-8")

    assert (
        runner.invoke(
            app,
            ["--cwd", str(dest), "import", str(export_file), "--replace"],
        ).exit_code
        == 0
    )
    active = _json(runner.invoke(app, ["--cwd", str(dest), "--json", "task", "active"]))
    assert active["result"]["task_id"] == "task-0001"
