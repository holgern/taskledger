"""Fake command runner for tests that don't need real subprocess execution."""

from __future__ import annotations

from pathlib import Path

from taskledger.services.command_runner import CommandResult


def fake_success(argv: tuple[str, ...], *, cwd: Path) -> CommandResult:
    """Return a successful command result without executing anything."""
    return CommandResult(returncode=0, stdout="ok\n", stderr="")


def fake_failure(argv: tuple[str, ...], *, cwd: Path) -> CommandResult:
    """Return a failed command result without executing anything."""
    return CommandResult(returncode=2, stdout="", stderr="boom\n")
