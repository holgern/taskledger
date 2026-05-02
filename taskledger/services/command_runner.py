from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple


class CommandResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


def run_command(argv: tuple[str, ...], *, cwd: Path) -> CommandResult:
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)
