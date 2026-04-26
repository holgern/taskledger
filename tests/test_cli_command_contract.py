from __future__ import annotations

import inspect
import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app


REMOVED_COMMANDS = {
    "task new",
    "task clear-active",
    "implement add-change",
    "validate add-check",
    "file link",
    "file unlink",
    "link link",
    "link unlink",
}


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _registered_command_paths() -> set[str]:
    paths = {command.name for command in app.registered_commands}
    for group in app.registered_groups:
        for command in group.typer_instance.registered_commands:
            paths.add(f"{group.name} {command.name}")
    paths.add("doctor")
    return {path for path in paths if path is not None}


def _callbacks() -> list[tuple[str, object]]:
    callbacks: list[tuple[str, object]] = []
    for command in app.registered_commands:
        if command.name is not None:
            callbacks.append((command.name, command.callback))
    for group in app.registered_groups:
        for command in group.typer_instance.registered_commands:
            if command.name is not None:
                callbacks.append((f"{group.name} {command.name}", command.callback))
    return callbacks


def test_removed_aliases_are_not_registered() -> None:
    assert REMOVED_COMMANDS.isdisjoint(_registered_command_paths())


def test_task_scoped_commands_do_not_accept_positional_task_refs() -> None:
    offenders: list[str] = []
    for command, callback in _callbacks():
        signature = inspect.signature(callback)
        for parameter in signature.parameters.values():
            annotation = str(parameter.annotation)
            if "typer.Argument" not in annotation:
                continue
            if "Task ref. Defaults to the active task." in annotation:
                offenders.append(f"{command}:{parameter.name}")
    assert not offenders


def test_commands_do_not_register_local_json_options() -> None:
    offenders: list[str] = []
    for command, callback in _callbacks():
        if command == "taskledger":
            continue
        for parameter in inspect.signature(callback).parameters.values():
            if "--json" in str(parameter.annotation):
                offenders.append(f"{command}:{parameter.name}")
    assert not offenders


def test_positional_task_ref_is_rejected_and_task_option_works(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Contract Task",
                "--slug",
                "contract-task",
                "--description",
                "Exercise the strict command grammar.",
            ],
        ).exit_code
        == 0
    )

    positional = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "plan", "start", "contract-task"],
    )
    assert positional.exit_code != 0

    explicit = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "plan", "start", "--task", "contract-task"],
    )
    assert explicit.exit_code == 0, explicit.stdout
    payload = json.loads(explicit.stdout)
    assert payload["ok"] is True
    assert payload["result"]["task_id"] == "task-0001"


def test_global_json_only_for_task_show(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Json Task",
                "--slug",
                "json-task",
                "--description",
                "Exercise global JSON output.",
            ],
        ).exit_code
        == 0
    )

    local = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "show", "--task", "json-task", "--json"],
    )
    assert local.exit_code != 0

    global_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "task", "show", "--task", "json-task"],
    )
    assert global_result.exit_code == 0, global_result.stdout
    payload = json.loads(global_result.stdout)
    assert payload["command"] == "task.show"
    assert payload["ok"] is True
