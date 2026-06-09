from __future__ import annotations

import sys

from taskledger.services.command_runner import run_command


def test_run_command_preserves_nonzero_python_exit_code(tmp_path):
    result = run_command(
        (sys.executable, "-c", "raise SystemExit(3)"),
        cwd=tmp_path,
    )

    assert result.returncode == 3
    assert result.stdout == ""
    assert result.stderr == ""
