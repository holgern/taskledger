from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.services.doctor import inspect_v2_project
from taskledger.storage.meta import StorageMeta
from taskledger.storage.paths import resolve_project_paths
from taskledger.storage.project_config import load_project_config_overrides


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _write_storage_root(path: Path) -> None:
    for directory in (
        path,
        path / "intros",
        path / "tasks",
        path / "events",
        path / "indexes",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for index_name in ("active_locks.json", "dependencies.json", "introductions.json"):
        (path / "indexes" / index_name).write_text("[]\n", encoding="utf-8")
    meta = StorageMeta(created_with_taskledger="test")
    (path / "storage.yaml").write_text(
        yaml.safe_dump(meta.to_dict(), sort_keys=False), encoding="utf-8"
    )


def test_init_writes_root_taskledger_toml_and_default_storage(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--root", str(tmp_path), "init"])

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "taskledger.toml").exists()
    assert (tmp_path / ".taskledger" / "storage.yaml").exists()
    assert not (tmp_path / ".taskledger" / "project.toml").exists()


def test_init_with_external_taskledger_dir_uses_directory_directly(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "repo"
    storage = tmp_path / "cloud" / "taskledger" / "repo"
    workspace.mkdir()

    result = runner.invoke(
        app,
        ["--root", str(workspace), "init", "--taskledger-dir", str(storage)],
    )

    assert result.exit_code == 0, result.stdout
    config_text = (workspace / "taskledger.toml").read_text(encoding="utf-8")
    assert str(storage) in config_text
    assert (storage / "storage.yaml").exists()
    assert (storage / "tasks").is_dir()
    assert not (storage / ".taskledger").exists()
    assert not (workspace / ".taskledger").exists()


def test_task_create_uses_configured_external_storage(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    storage = tmp_path / "cloud" / "taskledger" / "repo"
    workspace.mkdir()

    init_result = runner.invoke(
        app,
        ["--root", str(workspace), "init", "--taskledger-dir", str(storage)],
    )
    assert init_result.exit_code == 0, init_result.stdout

    result = runner.invoke(
        app,
        [
            "--root",
            str(workspace),
            "task",
            "create",
            "External storage task",
            "--description",
            "Write task data outside the repo.",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert any((storage / "tasks").glob("task-*"))
    assert not (workspace / ".taskledger" / "tasks").exists()


def test_relative_taskledger_dir_is_relative_to_config_path(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "taskledger.toml").write_text(
        'config_version = 1\ntaskledger_dir = "../state/repo"\n',
        encoding="utf-8",
    )

    paths = resolve_project_paths(workspace)

    assert paths.taskledger_dir == (tmp_path / "state" / "repo").resolve()


def test_cli_discovers_taskledger_toml_from_subdirectory(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path / "repo"
    subdir = workspace / "src" / "pkg"
    subdir.mkdir(parents=True)
    assert runner.invoke(app, ["--root", str(workspace), "init"]).exit_code == 0

    monkeypatch.chdir(subdir)
    result = runner.invoke(app, ["--json", "status"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["result"]["workspace_root"] == str(workspace)
    assert payload["result"]["config_path"] == str(workspace / "taskledger.toml")


def test_legacy_dot_taskledger_without_root_config_still_resolves(
    tmp_path: Path,
) -> None:
    _write_storage_root(tmp_path / ".taskledger")

    paths = resolve_project_paths(tmp_path)

    assert paths.taskledger_dir == (tmp_path / ".taskledger").resolve()
    assert paths.config_path == tmp_path / "taskledger.toml"


def test_legacy_project_toml_is_used_as_fallback_config(tmp_path: Path) -> None:
    legacy_dir = tmp_path / ".taskledger"
    _write_storage_root(legacy_dir)
    (legacy_dir / "project.toml").write_text(
        "default_source_max_chars = 42\n", encoding="utf-8"
    )

    paths = resolve_project_paths(tmp_path)

    assert paths.config_path == legacy_dir / "project.toml"
    assert load_project_config_overrides(paths)["default_source_max_chars"] == 42


def test_invalid_taskledger_toml_returns_json_error(tmp_path: Path) -> None:
    (tmp_path / "taskledger.toml").write_text(
        "taskledger_dir = [1, 2, 3]\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["--root", str(tmp_path), "--json", "status"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "taskledger_dir" in payload["error"]["message"]


def test_dot_taskledger_toml_wins_and_doctor_warns(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    hidden_storage = tmp_path / "state-hidden"
    canonical_storage = tmp_path / "state-canonical"
    _write_storage_root(hidden_storage)
    _write_storage_root(canonical_storage)
    (workspace / ".taskledger.toml").write_text(
        f'config_version = 1\ntaskledger_dir = "{hidden_storage}"\n',
        encoding="utf-8",
    )
    (workspace / "taskledger.toml").write_text(
        f'config_version = 1\ntaskledger_dir = "{canonical_storage}"\n',
        encoding="utf-8",
    )

    paths = resolve_project_paths(workspace)
    doctor = inspect_v2_project(workspace)

    assert paths.taskledger_dir == hidden_storage.resolve()
    assert any(
        "Both taskledger.toml and .taskledger.toml exist" in warning
        for warning in doctor["warnings"]
    )


def test_doctor_warns_on_legacy_project_toml(tmp_path: Path) -> None:
    legacy_dir = tmp_path / ".taskledger"
    _write_storage_root(legacy_dir)
    (legacy_dir / "project.toml").write_text("default_source_max_chars = 99\n")

    doctor = inspect_v2_project(tmp_path)

    assert any("Legacy config location" in warning for warning in doctor["warnings"])
