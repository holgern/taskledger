from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def test_taskledger_init_item_and_memory_workflow(tmp_path: Path) -> None:
    init_result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    item_create = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "parser-fix",
            "--text",
            "Repair the parser handling.",
        ],
    )
    item_list = runner.invoke(app, ["--cwd", str(tmp_path), "item", "list"])
    item_show = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "item", "show", "item-0001"],
    )
    memory_create = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "memory",
            "create",
            "Failing tests",
            "--text",
            "pytest output",
        ],
    )
    memory_list = runner.invoke(app, ["--cwd", str(tmp_path), "memory", "list"])
    memory_show = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "memory", "show", "failing-tests"],
    )

    assert init_result.exit_code == 0
    assert (tmp_path / ".taskledger").exists()
    assert item_create.exit_code == 0
    assert item_list.exit_code == 0
    assert "item-0001" in item_list.stdout
    assert item_show.exit_code == 0
    assert "parser-fix" in item_show.stdout
    assert memory_create.exit_code == 0
    assert memory_list.exit_code == 0
    assert "failing-tests" in memory_list.stdout
    assert memory_show.exit_code == 0
    assert "pytest output" in memory_show.stdout


def test_taskledger_status_json_reports_counts(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "sale-line-fix",
            "--text",
            "Implement the fix.",
        ],
    )

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "status"])

    assert result.exit_code == 0
    assert '"kind": "taskledger_status"' in result.stdout
    assert '"work_items": 1' in result.stdout


def test_taskledger_removed_plan_pbi_and_migrate_commands(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])

    for command in (["plan", "--help"], ["pbi", "--help"], ["migrate", "--help"]):
        result = runner.invoke(app, ["--cwd", str(tmp_path), *command])
        assert result.exit_code != 0
