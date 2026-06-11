from __future__ import annotations

import sys

import pytest

from taskledger.services.command_runner import run_command


# sw: f=specs/behavior/features/command_runner/command-runner.feature
# sw: s=@bdd-command-runner-run-command-preserves-nonzero-python-exit-code
def test_run_command_preserves_nonzero_python_exit_code(tmp_path):
    result = run_command(
        (sys.executable, "-c", "raise SystemExit(3)"),
        cwd=tmp_path,
    )

    assert result.returncode == 3
    assert result.stdout == ""
    assert result.stderr == ""


# sw: f=specs/behavior/features/command_runner/command-runner.feature
# sw: s=@bdd-command-runner-run-command-preserves-zero-python-exit-code
def test_run_command_preserves_zero_python_exit_code(tmp_path):
    result = run_command(
        (sys.executable, "-c", "pass"),
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_run_command_propagates_parent_keyboard_interrupt(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(KeyboardInterrupt):
        run_command((sys.executable, "-c", "pass"), cwd=tmp_path)
