"""Cover top-level CLI commands in taskledger/cli.py.

These commands route through _emit_project_payload and _emit_search_results,
which are also exercised indirectly by these tests.
"""
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


def test_board_command(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "board"])
    assert result.exit_code == 0


def test_board_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "board"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "work_items" in payload


def test_next_command_returns_none(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "next"])
    assert result.exit_code == 0
    assert "no next action" in result.stdout


def test_doctor_command(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "doctor"])
    assert result.exit_code == 0


def test_doctor_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "doctor"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "counts" in payload


def test_report_command(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "report"])
    assert result.exit_code == 0


def test_report_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "report"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "taskledger_report"


def test_export_command(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "export"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "project_export"


def test_export_command_with_bodies(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(
        app, ["--cwd", str(tmp_path), "--json", "export", "--include-bodies"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "project_export"


def test_import_command(tmp_path: Path) -> None:
    _init_project(tmp_path)

    # First export to get valid payload
    export_result = runner.invoke(
        app, ["--cwd", str(tmp_path), "--json", "export"]
    )
    assert export_result.exit_code == 0
    export_file = tmp_path / "export.json"
    export_file.write_text(export_result.stdout, encoding="utf-8")

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "import", str(export_file)],
    )
    assert result.exit_code == 0
    assert f"imported taskledger from {export_file}" in result.stdout


def test_import_command_replace(tmp_path: Path) -> None:
    _init_project(tmp_path)

    export_result = runner.invoke(
        app, ["--cwd", str(tmp_path), "--json", "export"]
    )
    export_file = tmp_path / "export.json"
    export_file.write_text(export_result.stdout, encoding="utf-8")

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "import", str(export_file), "--replace"],
    )
    assert result.exit_code == 0


def test_import_command_missing_file(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "import",
            str(tmp_path / "nonexistent.json"),
        ],
    )
    assert result.exit_code == 1


def test_snapshot_command(tmp_path: Path) -> None:
    _init_project(tmp_path)
    output_dir = tmp_path / "snapshots"

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "snapshot",
            "--output-dir",
            str(output_dir),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "project_snapshot"
    assert output_dir.exists()


def test_snapshot_command_with_options(tmp_path: Path) -> None:
    _init_project(tmp_path)
    output_dir = tmp_path / "snapshots2"

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "snapshot",
            "--output-dir",
            str(output_dir),
            "--include-bodies",
            "--include-run-artifacts",
        ],
    )
    assert result.exit_code == 0


def test_search_command_with_results(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "sample.py").write_text("hello world\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Search Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app, ["--cwd", str(tmp_path), "search", "hello"]
    )
    assert result.exit_code == 0
    assert "SEARCH" in result.stdout


def test_search_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "sample.py").write_text("hello\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Search Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app, ["--cwd", str(tmp_path), "--json", "search", "hello"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)


def test_search_command_with_repo(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "sample.py").write_text("hello\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Search Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "search",
            "hello",
            "--repo",
            "search-repo",
            "--limit",
            "10",
        ],
    )
    assert result.exit_code == 0


def test_grep_command(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "grep_target.py").write_text("import os\nhello world\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Grep Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "grep", "import"],
    )
    assert result.exit_code == 0
    assert "GREP" in result.stdout


def test_grep_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "target.py").write_text("match_me\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Grep Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app, ["--cwd", str(tmp_path), "--json", "grep", "match_me"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)


def test_grep_command_with_repo(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "target.py").write_text("match_me_here\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Grep2 Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "grep",
            "match_me",
            "--repo",
            "grep2-repo",
            "--limit",
            "5",
        ],
    )
    assert result.exit_code == 0


def test_symbols_command(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "mod.py").write_text("def foo(): pass\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Sym Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "symbols", "foo"],
    )
    assert result.exit_code == 0
    assert "SYMBOLS" in result.stdout


def test_symbols_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "mod.py").write_text("def foo(): pass\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Sym Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app, ["--cwd", str(tmp_path), "--json", "symbols", "foo"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)


def test_deps_command(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    module_dir = repo_dir / "my_module"
    module_dir.mkdir(parents=True)
    (module_dir / "__manifest__.py").write_text(
        "{'name': 'my_module', 'depends': ['base', 'sale']}\n",
        encoding="utf-8",
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Dep Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "deps", "dep-repo", "my_module"],
    )
    assert result.exit_code == 0
    assert "MODULE my_module" in result.stdout
    assert "base" in result.stdout


def test_deps_command_json(tmp_path: Path) -> None:
    _init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    module_dir = repo_dir / "other_mod"
    module_dir.mkdir(parents=True)
    (module_dir / "__manifest__.py").write_text(
        "{'name': 'other_mod', 'depends': []}\n",
        encoding="utf-8",
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Dep2 Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "deps", "dep2-repo", "other_mod"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["module"] == "other_mod"


def test_deps_command_missing_repo(tmp_path: Path) -> None:
    _init_project(tmp_path)

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "deps", "no-such-repo", "module"],
    )
    assert result.exit_code == 1


def test_status_command_launch_error(tmp_path: Path) -> None:
    """status on a non-initialized directory triggers the LaunchError path."""
    result = runner.invoke(app, ["--cwd", str(tmp_path), "status"])
    assert result.exit_code == 1


def test_status_full_launch_error(tmp_path: Path) -> None:
    """status --full on a non-initialized directory triggers LaunchError."""
    result = runner.invoke(app, ["--cwd", str(tmp_path), "status", "--full"])
    assert result.exit_code == 1
