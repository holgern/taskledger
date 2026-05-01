from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.ledger_config import LedgerConfigPatch, update_ledger_config
from taskledger.storage.paths import load_project_locator


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(app, ["--cwd", str(tmp_path), *args])


def _set_counter(tmp_path: Path, number: int, ref: str = "main") -> None:
    locator = load_project_locator(tmp_path)
    update_ledger_config(
        locator.config_path,
        LedgerConfigPatch(ref=ref, next_task_number=number),
    )


def test_two_ledgers_can_each_have_task_0030_and_hide_active_task(
    tmp_path: Path,
) -> None:
    result = _invoke(tmp_path, "init")
    assert result.exit_code == 0, result.stdout

    _set_counter(tmp_path, 30)
    result = _invoke(tmp_path, "ledger", "fork", "feature-a")
    assert result.exit_code == 0, result.stdout
    result = _invoke(tmp_path, "task", "create", "Feature task")
    assert result.exit_code == 0, result.stdout
    assert "task-0030" in result.stdout
    result = _invoke(tmp_path, "task", "activate", "task-0030")
    assert result.exit_code == 0, result.stdout

    # Simulate Git checkout restoring main's checked-in ledger pointer and counter.
    _set_counter(tmp_path, 30, ref="main")
    result = _invoke(tmp_path, "task", "create", "Main hotfix")
    assert result.exit_code == 0, result.stdout
    assert "task-0030" in result.stdout

    # Feature active task is not visible from the main ledger.
    result = _invoke(tmp_path, "task", "active")
    assert result.exit_code != 0
    assert "Feature task" not in result.stdout

    assert (
        tmp_path / ".taskledger" / "ledgers" / "main" / "tasks" / "task-0030"
    ).is_dir()
    assert (
        tmp_path / ".taskledger" / "ledgers" / "feature-a" / "tasks" / "task-0030"
    ).is_dir()


def test_ledger_fork_switch_status_and_doctor(tmp_path: Path) -> None:
    assert _invoke(tmp_path, "init").exit_code == 0

    result = _invoke(tmp_path, "ledger", "status")
    assert result.exit_code == 0, result.stdout
    assert "Ledger ref: main" in result.stdout

    result = _invoke(tmp_path, "ledger", "fork", "feature-a")
    assert result.exit_code == 0, result.stdout
    assert "forked ledger main -> feature-a" in result.stdout

    result = _invoke(tmp_path, "ledger", "list")
    assert result.exit_code == 0, result.stdout
    assert "feature-a (current)" in result.stdout

    result = _invoke(tmp_path, "ledger", "switch", "main")
    assert result.exit_code == 0, result.stdout
    assert "switched feature-a -> main" in result.stdout

    result = _invoke(tmp_path, "ledger", "doctor")
    assert result.exit_code == 0, result.stdout
    assert "Healthy: yes" in result.stdout


def test_ledger_adopt_renumbers_on_collision(tmp_path: Path) -> None:
    assert _invoke(tmp_path, "init").exit_code == 0
    assert _invoke(tmp_path, "ledger", "fork", "feature-a").exit_code == 0
    assert _invoke(tmp_path, "task", "create", "Feature task").exit_code == 0
    assert _invoke(tmp_path, "ledger", "switch", "main").exit_code == 0
    _set_counter(tmp_path, 1, ref="main")
    assert _invoke(tmp_path, "task", "create", "Main task").exit_code == 0

    result = _invoke(tmp_path, "ledger", "adopt", "--from", "feature-a", "task-0001")
    assert result.exit_code == 0, result.stdout
    assert "renumbered" in result.stdout
    assert (
        tmp_path / ".taskledger" / "ledgers" / "main" / "tasks" / "task-0002"
    ).is_dir()


def test_doctor_reports_legacy_unscoped_state(tmp_path: Path) -> None:
    assert _invoke(tmp_path, "init").exit_code == 0
    legacy_tasks = tmp_path / ".taskledger" / "tasks"
    legacy_tasks.mkdir()

    result = _invoke(tmp_path, "ledger", "doctor")
    assert result.exit_code == 0, result.stdout
    assert "Legacy unscoped path exists" in result.stdout


def test_release_json_includes_ledger_ref(tmp_path: Path) -> None:
    assert _invoke(tmp_path, "init").exit_code == 0
    assert _invoke(tmp_path, "task", "create", "Release task").exit_code == 0
    task_md = (
        tmp_path
        / ".taskledger"
        / "ledgers"
        / "main"
        / "tasks"
        / "task-0001"
        / "task.md"
    )
    text = task_md.read_text(encoding="utf-8")
    text = text.replace("status: draft", "status: done")
    text = text.replace("status_stage: draft", "status_stage: done")
    task_md.write_text(text, encoding="utf-8")

    result = _invoke(
        tmp_path,
        "--json",
        "release",
        "tag",
        "0.1.0",
        "--at-task",
        "task-0001",
    )
    assert result.exit_code == 0, result.stdout
    assert '"ledger_ref": "main"' in result.stdout
