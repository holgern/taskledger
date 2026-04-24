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
            ["--cwd", str(source_root), "plan", "start", "migrate-v2"],
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
                "migrate-v2",
                "--text",
                "## Goal\n\nShip export support.",
            ],
        ).exit_code
        == 0
    )

    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "--json", "export"],
    )
    assert export_result.exit_code == 0
    export_payload = json.loads(export_result.stdout)
    assert export_payload["v2"]["tasks"][0]["slug"] == "migrate-v2"
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
        ["--cwd", str(dest_root), "--json", "task", "show", "migrate-v2"],
    )
    assert show_result.exit_code == 0
    task_payload = json.loads(show_result.stdout)
    assert task_payload["task"]["latest_plan_version"] == 1
