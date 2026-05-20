from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.cli import app


def _runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _runner()


def _json(result) -> dict[str, object]:
    return json.loads(result.stdout)


def _append_pipeline_config(path: Path, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    path.write_text(f"{current.rstrip()}\n\n{text.strip()}\n", encoding="utf-8")


def _enabled_pipeline_config() -> str:
    return """
[worker_pipeline]
enabled = true
name = "tdd-four-context"
mode = "guided"

[[worker_pipeline.steps]]
id = "planner"
lifecycle_stage = "planning"
base_context = "planner"

[[worker_pipeline.steps]]
id = "tester"
label = "Test Writer"
lifecycle_stage = "implementation"
base_context = "implementer"
kind = "check"
test_command_policy = "may_fail"

[[worker_pipeline.steps]]
id = "coder"
lifecycle_stage = "implementation"
base_context = "implementer"
kind = "todo"
test_command_policy = "must_pass"

[[worker_pipeline.steps]]
id = "reviewer"
lifecycle_stage = "review"
base_context = "code-reviewer"
kind = "review"
"""


def _disabled_pipeline_config() -> str:
    return """
[worker_pipeline]
name = "disabled-pipeline"

[[worker_pipeline.steps]]
id = "planner"
lifecycle_stage = "planning"
base_context = "planner"
"""


def test_pipeline_commands_print_no_config_message(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0

    for command in (["pipeline", "show"], ["pipeline", "list"], ["pipeline", "next"]):
        result = runner.invoke(app, ["--cwd", str(tmp_path), *command])
        assert result.exit_code == 0, result.stdout
        assert result.stdout.strip() == "No worker pipeline configured."


def test_pipeline_commands_print_disabled_message(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0
    _append_pipeline_config(tmp_path / "taskledger.toml", _disabled_pipeline_config())

    for command in (["pipeline", "show"], ["pipeline", "list"], ["pipeline", "next"]):
        result = runner.invoke(app, ["--cwd", str(tmp_path), *command])
        assert result.exit_code == 0, result.stdout
        assert result.stdout.strip() == "Worker pipeline is disabled."


def test_pipeline_show_and_list_render_enabled_config(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0
    _append_pipeline_config(tmp_path / "taskledger.toml", _enabled_pipeline_config())

    show_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "pipeline", "show"],
    )
    assert show_result.exit_code == 0, show_result.stdout
    show_payload = _json(show_result)
    assert show_payload["result"]["configured"] is True
    assert show_payload["result"]["enabled"] is True
    assert show_payload["result"]["pipeline"]["name"] == "tdd-four-context"

    list_result = runner.invoke(app, ["--cwd", str(tmp_path), "pipeline", "list"])
    assert list_result.exit_code == 0, list_result.stdout
    assert "planner" in list_result.stdout
    assert "Test Writer" in list_result.stdout
    assert "reviewer" in list_result.stdout


def test_pipeline_next_returns_planner_before_plan_acceptance(tmp_path: Path) -> None:
    assert runner.invoke(app, ["--cwd", str(tmp_path), "init"]).exit_code == 0
    _append_pipeline_config(tmp_path / "taskledger.toml", _enabled_pipeline_config())
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Pipeline task",
                "--slug",
                "pipeline-task",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "pipeline-task"],
        ).exit_code
        == 0
    )

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "pipeline", "next"])

    assert result.exit_code == 0, result.stdout
    payload = _json(result)
    assert payload["result"]["step"]["id"] == "planner"
    assert payload["result"]["reason"] == "No accepted plan exists yet."
