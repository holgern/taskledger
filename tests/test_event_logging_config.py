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


def _enable_event_logging(tmp_path: Path) -> None:
    config_path = tmp_path / "taskledger.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\n[event_logging]\nenabled = true\n",
        encoding="utf-8",
    )


def _create_and_activate_task(tmp_path: Path, slug: str = "test-task") -> None:
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Test task",
                "--slug",
                slug,
                "--description",
                "A test task.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", slug],
        ).exit_code
        == 0
    )


# -- default-off tests --


def test_runtime_events_disabled_by_default(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _create_and_activate_task(tmp_path)

    event_files = sorted((tmp_path / ".taskledger").glob("**/events/*.ndjson"))
    assert event_files == []

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "task", "events", "--task", "test-task"],
    )
    assert result.exit_code == 0


def test_task_events_shows_empty_when_disabled(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _create_and_activate_task(tmp_path)

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "task", "events"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["items"] == []


def test_lock_break_no_events_by_default(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "lock-test",
                "--description",
                "Test lock break events.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(tmp_path), "plan", "start", "--task", "lock-test"]
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "lock",
            "break",
            "--task",
            "lock-test",
            "--reason",
            "test",
        ],
    )
    assert result.exit_code == 0

    event_files = sorted((tmp_path / ".taskledger").glob("**/events/*.ndjson"))
    assert event_files == []


# -- opt-in tests --


def test_runtime_events_enabled_writes_events(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _enable_event_logging(tmp_path)
    _create_and_activate_task(tmp_path)

    event_files = sorted((tmp_path / ".taskledger").glob("**/events/*.ndjson"))
    assert len(event_files) > 0

    events = []
    for path in event_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))

    assert any(e["event"] == "task.created" for e in events)


def test_lock_break_writes_events_when_enabled(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _enable_event_logging(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "lock-enabled",
                "--description",
                "Test lock break events enabled.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "lock-enabled"],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "lock",
            "break",
            "--task",
            "lock-enabled",
            "--reason",
            "test",
        ],
    )
    assert result.exit_code == 0

    event_files = sorted((tmp_path / ".taskledger").glob("**/events/*.ndjson"))
    assert len(event_files) > 0
    events = []
    for path in event_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    assert any(e["event"] == "repair.lock_broken" for e in events)


def test_existing_events_readable_after_disable(tmp_path: Path) -> None:
    _init_project(tmp_path)
    _enable_event_logging(tmp_path)
    _create_and_activate_task(tmp_path)

    # Verify events were written
    event_files = sorted((tmp_path / ".taskledger").glob("**/events/*.ndjson"))
    assert len(event_files) > 0

    # Disable event logging
    config_path = tmp_path / "taskledger.toml"
    text = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        text.replace("enabled = true", "enabled = false"),
        encoding="utf-8",
    )

    # Create another task - should not produce new events
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Second task",
                "--slug",
                "second-task",
                "--description",
                "After disable.",
            ],
        ).exit_code
        == 0
    )

    # Old events still readable
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "task", "events", "--all"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert len(payload["result"]["items"]) > 0
