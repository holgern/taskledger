from __future__ import annotations

from taskledger.cli import app
from taskledger.command_inventory import (
    COMMAND_METADATA,
    HUMAN_ORIENTED,
    REPAIR,
    STABLE_FOR_AGENTS,
)


def _registered_command_paths() -> set[str]:
    paths = {command.name for command in app.registered_commands}
    for group in app.registered_groups:
        group_name = group.name
        typer_app = group.typer_instance
        for command in typer_app.registered_commands:
            paths.add(f"{group_name} {command.name}")
    paths.add("doctor")
    return {path for path in paths if path is not None}


def test_registered_commands_have_inventory_metadata() -> None:
    assert _registered_command_paths() == set(COMMAND_METADATA)


def test_inventory_marks_core_and_repair_commands() -> None:
    assert COMMAND_METADATA["task create"][0] == STABLE_FOR_AGENTS
    assert COMMAND_METADATA["plan approve"][0] == STABLE_FOR_AGENTS
    assert COMMAND_METADATA["implement restart"][0] == STABLE_FOR_AGENTS
    assert COMMAND_METADATA["implement resume"][0] == STABLE_FOR_AGENTS
    assert COMMAND_METADATA["task uncancel"][0] == STABLE_FOR_AGENTS
    assert COMMAND_METADATA["serve"][0] == HUMAN_ORIENTED
    assert COMMAND_METADATA["lock break"][0] == REPAIR
    assert COMMAND_METADATA["doctor"][0] == REPAIR


def test_mutating_commands_are_not_marked_safe_read_only() -> None:
    mutating_suffixes = {
        "activate",
        "add",
        "change",
        "answer",
        "approve",
        "artifact",
        "break",
        "cancel",
        "check",
        "close",
        "command",
        "create",
        "deactivate",
        "deviation",
        "dismiss",
        "done",
        "edit",
        "finish",
        "index",
        "link",
        "log",
        "propose",
        "reject",
        "remove",
        "resume",
        "revise",
        "scan-changes",
        "start",
        "task",
        "uncancel",
        "undone",
        "unlink",
        "waive",
    }

    for command, spec in COMMAND_METADATA.items():
        assert not (
            command.split()[-1] in mutating_suffixes and spec.effect == "safe_read_only"
        ), command
