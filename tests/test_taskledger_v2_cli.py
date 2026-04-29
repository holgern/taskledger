from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import yaml
from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.task_store import (
    list_runs,
    resolve_run,
    resolve_task,
    save_run,
    save_task,
)


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _prepare_focused_context_task(tmp_path: Path) -> str:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "focused-contexts",
                "--description",
                "Exercise focused worker contexts.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "focused-contexts"],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0
    plan_text = """---
goal: Render focused worker contexts.
acceptance_criteria:
  - id: ac-0001
    text: Focused contexts render correctly.
todos:
  - id: todo-0001
    text: Implement the focused context feature.
    validation_hint: pytest tests/test_taskledger_v2_cli.py -q
---

# Plan

Ship focused worker contexts.
"""
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "propose",
                "--text",
                plan_text,
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Ready to implement.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "implement", "start"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "change",
                "--path",
                "taskledger/services/handoff.py",
                "--kind",
                "edit",
                "--summary",
                "Added focused worker context handling.",
            ],
        ).exit_code
        == 0
    )
    return "run-0002"


def _json(result) -> dict[str, object]:
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    return payload


def _prepare_resumable_implementation_task(tmp_path: Path) -> tuple[str, str]:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "resume-task",
                "--description",
                "Exercise implement resume.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "resume-task"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "plan", "start", "--task", "resume-task"],
        ).exit_code
        == 0
    )
    plan_text = """---
goal: Recover a running implementation.
acceptance_criteria:
  - id: ac-0001
    text: Implementation can resume safely.
todos:
  - id: todo-0001
    text: Add the resume flow.
    validation_hint: pytest tests/test_taskledger_v2_cli.py -q
---

# Plan

Recover a running implementation after its lock is broken.
"""
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "propose",
                "--task",
                "resume-task",
                "--text",
                plan_text,
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "--task",
                "resume-task",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Ready to implement.",
            ],
        ).exit_code
        == 0
    )
    start = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "implement",
                "start",
                "--task",
                "resume-task",
            ],
        )
    )
    return "task-0001", str(start["result"]["run_id"])


def _break_task_lock(tmp_path: Path, task_ref: str = "resume-task") -> None:
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lock",
            "break",
            "--task",
            task_ref,
            "--reason",
            "Recover stale implementation lock.",
        ],
    )
    assert result.exit_code == 0, result.stdout


def test_v2_task_lifecycle_and_handoff(tmp_path: Path) -> None:
    _init_project(tmp_path)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Rewrite V2",
                "--slug",
                "rewrite-v2",
                "--description",
                "Rewrite taskledger to the new design.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "rewrite-v2"],
        ).exit_code
        == 0
    )
    assert runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "can", "plan"],
    ).stdout
    start_plan = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "plan", "start", "--task", "rewrite-v2"],
        )
    )
    assert start_plan["result"]["status_stage"] == "draft"
    assert start_plan["result"]["active_stage"] == "planning"
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "add",
                "--text",
                "Should exports include v2?",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "question",
                "answer",
                "q-0001",
                "--text",
                "Yes.",
            ],
        ).exit_code
        == 0
    )
    propose_plan = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "plan",
                "propose",
                "--task",
                "rewrite-v2",
                "--criterion",
                "Ship the rewrite safely.",
                "--text",
                "## Goal\n\nShip the v2 rewrite.",
            ],
        )
    )
    assert propose_plan["result"]["status_stage"] == "plan_review"
    assert propose_plan["result"]["active_stage"] is None
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "--task",
                "rewrite-v2",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Ready to implement.",
                "--allow-empty-todos",
                "--allow-lint-errors",
                "--reason",
                "test",
            ],
        ).exit_code
        == 0
    )
    start_impl = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "implement",
                "start",
                "--task",
                "rewrite-v2",
            ],
        )
    )
    assert start_impl["result"]["status_stage"] == "approved"
    assert start_impl["result"]["active_stage"] == "implementation"
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "log",
                "--task",
                "rewrite-v2",
                "--message",
                "wired new storage",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "change",
                "--task",
                "rewrite-v2",
                "--path",
                "taskledger/storage/task_store.py",
                "--kind",
                "edit",
                "--summary",
                "Added canonical v2 storage.",
            ],
        ).exit_code
        == 0
    )
    finish_impl = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "implement",
                "finish",
                "--task",
                "rewrite-v2",
                "--summary",
                "Implemented v2",
            ],
        )
    )
    assert finish_impl["result"]["status_stage"] == "implemented"
    assert finish_impl["result"]["active_stage"] is None
    start_validation = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "validate",
                "start",
                "--task",
                "rewrite-v2",
            ],
        )
    )
    assert start_validation["result"]["status_stage"] == "implemented"
    assert start_validation["result"]["active_stage"] == "validation"
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate",
                "check",
                "--task",
                "rewrite-v2",
                "--criterion",
                "ac-0001",
                "--status",
                "pass",
                "--evidence",
                "pytest -q",
            ],
        ).exit_code
        == 0
    )
    finish_validation = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "validate",
                "finish",
                "--task",
                "rewrite-v2",
                "--result",
                "passed",
                "--summary",
                "Validated v2",
            ],
        )
    )
    assert finish_validation["result"]["status_stage"] == "done"
    assert finish_validation["result"]["active_stage"] is None

    show_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "task", "show", "--task", "rewrite-v2"],
    )
    payload = _json(show_result)
    assert payload["command"] == "task.show"
    assert payload["result"]["task"]["status_stage"] == "done"
    assert payload["result"]["task"]["active_stage"] is None
    assert payload["result"]["task"]["accepted_plan_version"] == 1
    assert payload["result"]["changes"][0]["path"] == "taskledger/storage/task_store.py"

    handoff_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "handoff",
            "validation-context",
        ],
    )
    assert handoff_result.exit_code == 0
    assert "Code Changes" in handoff_result.stdout
    assert "taskledger/storage/task_store.py" in handoff_result.stdout

    doctor_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "doctor"],
    )
    doctor_payload = _json(doctor_result)
    assert doctor_payload["result"]["healthy"] is True

    reindex_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "reindex"],
    )
    reindex_payload = _json(reindex_result)
    assert reindex_payload["result"]["counts"] == {
        "introductions": 0,
        "locks": 0,
        "dependencies": 1,
    }


def test_failed_validation_restarts_implementation(tmp_path: Path) -> None:
    _init_project(tmp_path)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "Validation restart",
                "--slug",
                "validation-restart",
                "--description",
                "Exercise failed validation recovery.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "validation-restart"],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start"]).exit_code == 0

    plan_text = """---
goal: Exercise failed validation restart.
acceptance_criteria:
  - id: ac-0001
    text: Restarting implementation after failed validation works.
todos:
  - id: todo-0001
    text: Implement the initial version.
    validation_hint: pytest tests/test_taskledger_v2_cli.py -q
---

# Plan

Ship the initial implementation, fail validation, and restart implementation.
"""
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "propose",
                "--text",
                plan_text,
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Ready to implement.",
            ],
        ).exit_code
        == 0
    )

    start = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "implement", "start"])
    )
    first_implementation_run = start["result"]["run_id"]

    todo_list = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "todo", "list"])
    )
    todo_id = todo_list["result"]["todos"][0]["id"]
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo",
                "done",
                todo_id,
                "--evidence",
                "Initial implementation recorded.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "implement",
                "finish",
                "--summary",
                "Initial implementation complete.",
            ],
        ).exit_code
        == 0
    )

    validation_start = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "validate", "start"])
    )
    validation_run_id = validation_start["result"]["run_id"]

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "validate",
                "check",
                "--criterion",
                "ac-0001",
                "--status",
                "fail",
                "--evidence",
                "pytest failed",
            ],
        ).exit_code
        == 0
    )
    failed_validation = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "validate",
                "finish",
                "--result",
                "failed",
                "--summary",
                "Bug found during validation.",
            ],
        )
    )
    assert failed_validation["result"]["status_stage"] == "failed_validation"
    assert failed_validation["result"]["active_stage"] is None

    next_action = _json(
        runner.invoke(app, ["--cwd", str(tmp_path), "--json", "next-action"])
    )["result"]
    assert next_action["action"] == "implement-restart"
    assert (
        next_action["next_command"] == "taskledger implement restart --summary SUMMARY"
    )
    assert next_action["next_item"] == {
        "kind": "task",
        "id": "task-0001",
        "status_stage": "failed_validation",
    }
    assert next_action["commands"][0] == {
        "kind": "restart",
        "label": "Restart implementation",
        "command": "taskledger implement restart --summary SUMMARY",
        "primary": True,
    }

    can_restart = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "can", "implement-restart"],
        )
    )
    assert can_restart["result"]["ok"] is True

    restart = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "implement",
                "restart",
                "--summary",
                "Fix failed validation findings.",
            ],
        )
    )
    assert restart["command"] == "implement.restart"
    restart_result = restart["result"]
    assert restart_result["status_stage"] == "failed_validation"
    assert restart_result["active_stage"] == "implementation"
    assert restart_result["run_id"] != first_implementation_run
    assert restart_result["run"]["resumes_run_id"] == first_implementation_run
    assert restart_result["run"]["worklog"][:2] == [
        "Restart summary: Fix failed validation findings.",
        "Restarted after validation run run-0003 (failed).",
    ]

    validate_show = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "validate",
                "show",
                "--run",
                validation_run_id,
            ],
        )
    )
    assert validate_show["result"]["run"]["status"] == "failed"
    assert validate_show["result"]["run"]["result"] == "failed"

    task_show = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "--json",
                "task",
                "show",
                "--task",
                "validation-restart",
            ],
        )
    )
    assert task_show["result"]["task"]["status_stage"] == "implementing"
    assert (
        task_show["result"]["task"]["latest_implementation_run"]
        == restart_result["run_id"]
    )
    assert task_show["result"]["task"]["latest_validation_run"] == validation_run_id


def test_v2_lock_break_and_expired_lock_report(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "lock-task",
            "--description",
            "Task with a planning lock.",
        ],
    )
    runner.invoke(app, ["--cwd", str(tmp_path), "plan", "start", "--task", "lock-task"])

    lock_path = tmp_path / ".taskledger" / "tasks" / "task-0001" / "lock.yaml"
    payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    payload["expires_at"] = "2000-01-01T00:00:00+00:00"
    lock_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    doctor_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "doctor", "locks"],
    )
    assert doctor_result.exit_code == 0
    assert "task-0001" in doctor_result.stdout

    break_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "lock",
            "break",
            "--reason",
            "recover stale planning lock",
            "--task",
            "lock-task",
        ],
    )
    assert break_result.exit_code == 0
    assert _json(break_result)["result"]["command"] == "lock break"
    assert not lock_path.exists()


def test_implement_resume_reacquires_lock_after_break(tmp_path: Path) -> None:
    task_id, run_id = _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    payload = _json(result)
    resume = payload["result"]
    assert payload["command"] == "implement.resume"
    assert resume["run_id"] == run_id
    assert resume["status_stage"] == "implementing"
    assert resume["active_stage"] == "implementation"

    task_show = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "task", "show", "--task", "resume-task"],
        )
    )
    assert task_show["result"]["task"]["id"] == task_id
    assert task_show["result"]["task"]["active_stage"] == "implementation"


def test_implement_resume_does_not_create_new_run(tmp_path: Path) -> None:
    task_id, run_id = _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code == 0, result.stdout

    implementation_runs = [
        run for run in list_runs(tmp_path, task_id) if run.run_type == "implementation"
    ]
    assert len(implementation_runs) == 1
    assert implementation_runs[0].run_id == run_id


def test_implement_resume_requires_reason(tmp_path: Path) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "",
        ],
    )
    assert result.exit_code != 0
    assert "Implementation resume requires --reason." in result.stdout


def test_implement_resume_rejects_missing_accepted_plan(tmp_path: Path) -> None:
    task_id, _ = _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)
    task = resolve_task(tmp_path, task_id)
    save_task(tmp_path, replace(task, accepted_plan_version=None))

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code != 0
    assert "Implementation resume requires an accepted plan version." in result.stdout


def test_implement_resume_rejects_non_running_implementation_run(
    tmp_path: Path,
) -> None:
    task_id, run_id = _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)
    run = resolve_run(tmp_path, task_id, run_id)
    save_run(tmp_path, replace(run, status="finished"))

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code != 0
    assert (
        "Implementation resume requires a running implementation run." in result.stdout
    )


def test_implement_resume_rejects_non_implementation_run(tmp_path: Path) -> None:
    task_id, run_id = _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)
    run = resolve_run(tmp_path, task_id, run_id)
    save_run(tmp_path, replace(run, run_type="planning"))

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code != 0
    assert (
        "Implementation resume requires a running implementation run." in result.stdout
    )


def test_implement_resume_rejects_existing_lock(tmp_path: Path) -> None:
    _prepare_resumable_implementation_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code != 0
    assert "Implementation resume requires no active lock." in result.stdout


def test_implement_resume_rejects_completed_task(tmp_path: Path) -> None:
    task_id, _ = _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)
    task = resolve_task(tmp_path, task_id)
    save_task(tmp_path, replace(task, status_stage="implemented"))

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code != 0
    assert (
        "Implementation resume requires approved or implementing state."
        in result.stdout
    )


def test_implement_resume_rejects_cancelled_task(tmp_path: Path) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    cancel = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "cancel",
            "--task",
            "resume-task",
            "--reason",
            "Cancelled during recovery test.",
        ],
    )
    assert cancel.exit_code == 0, cancel.stdout

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "implement",
            "resume",
            "--task",
            "resume-task",
            "--reason",
            "Continue implementation after a stale lock break.",
        ],
    )
    assert result.exit_code != 0
    assert (
        "Implementation resume requires approved or implementing state."
        in result.stdout
    )


def test_task_uncancel_restores_cancelled_task_to_approved(tmp_path: Path) -> None:
    task_id, _ = _prepare_resumable_implementation_task(tmp_path)
    cancel = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "cancel",
            "--task",
            "resume-task",
            "--reason",
            "Cancelled accidentally.",
        ],
    )
    assert cancel.exit_code == 0, cancel.stdout

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "task",
            "uncancel",
            "--task",
            "resume-task",
            "--actor",
            "agent",
            "--allow-agent-uncancel",
            "--reason",
            "User explicitly requested continuation in the harness.",
        ],
    )
    payload = _json(result)
    uncancel = payload["result"]
    assert payload["command"] == "task.uncancel"
    assert uncancel["task_id"] == task_id
    assert uncancel["status_stage"] == "approved"
    assert uncancel["active_stage"] is None

    task_show = _json(
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "--json", "task", "show", "--task", "resume-task"],
        )
    )
    assert task_show["result"]["task"]["status_stage"] == "approved"


def test_next_action_after_uncancel_running_implementation_recommends_resume(
    tmp_path: Path,
) -> None:
    _, run_id = _prepare_resumable_implementation_task(tmp_path)
    cancel = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "cancel",
            "--task",
            "resume-task",
            "--reason",
            "Cancelled accidentally.",
        ],
    )
    assert cancel.exit_code == 0, cancel.stdout
    uncancel = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "uncancel",
            "--task",
            "resume-task",
            "--actor",
            "agent",
            "--allow-agent-uncancel",
            "--reason",
            "User explicitly requested continuation.",
        ],
    )
    assert uncancel.exit_code == 0, uncancel.stdout

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "next-action"])
    payload = _json(result)["result"]

    assert payload["status_stage"] == "approved"
    assert payload["action"] == "implement-resume"
    assert payload["next_command"] == (
        "taskledger implement resume --task task-0001 "
        '--reason "Reacquire implementation lock for existing running run."'
    )
    assert any(
        blocker["message"] == f"Missing active implementation lock for run {run_id}."
        for blocker in payload["blocking"]
    )


def test_can_implement_blocks_existing_running_run_after_uncancel(
    tmp_path: Path,
) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "cancel",
                "--task",
                "resume-task",
                "--reason",
                "Cancelled accidentally.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "uncancel",
                "--task",
                "resume-task",
                "--actor",
                "agent",
                "--allow-agent-uncancel",
                "--reason",
                "User explicitly requested continuation.",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(app, ["--cwd", str(tmp_path), "--json", "can", "implement"])
    payload = _json(result)["result"]

    assert payload["ok"] is False
    assert any(
        "running implementation run" in blocker["message"]
        and "taskledger implement resume" in blocker["command_hint"]
        for blocker in payload["blocking"]
    )


def test_can_implement_resume_after_uncancel_running_implementation(
    tmp_path: Path,
) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "cancel",
                "--task",
                "resume-task",
                "--reason",
                "Cancelled accidentally.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "uncancel",
                "--task",
                "resume-task",
                "--actor",
                "agent",
                "--allow-agent-uncancel",
                "--reason",
                "User explicitly requested continuation.",
            ],
        ).exit_code
        == 0
    )

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "can", "implement-resume"],
    )
    payload = _json(result)["result"]

    assert payload["ok"] is True
    assert payload["reason"] == "Implementation resume is ready."


def test_uncancel_non_cancelled_orphan_hints_resume(tmp_path: Path) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    _break_task_lock(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "task",
            "uncancel",
            "--task",
            "resume-task",
            "--actor",
            "agent",
            "--allow-agent-uncancel",
            "--reason",
            "User requested continuation.",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert "not cancelled" in payload["error"]["message"]
    assert any(
        "taskledger implement resume" in item
        for item in payload["error"]["remediation"]
    )


def test_task_uncancel_rejects_active_stage_target(tmp_path: Path) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    cancel = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "cancel",
            "--task",
            "resume-task",
            "--reason",
            "Cancelled accidentally.",
        ],
    )
    assert cancel.exit_code == 0, cancel.stdout

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "task",
            "uncancel",
            "--task",
            "resume-task",
            "--actor",
            "agent",
            "--allow-agent-uncancel",
            "--to",
            "implementing",
            "--reason",
            "User explicitly requested continuation in the harness.",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid uncancel target: implementing" in result.stdout


def test_repair_task_human_output_records_inspection_and_recovery_hint(
    tmp_path: Path,
) -> None:
    _prepare_resumable_implementation_task(tmp_path)
    cancel = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "cancel",
            "--task",
            "resume-task",
            "--reason",
            "Cancelled accidentally.",
        ],
    )
    assert cancel.exit_code == 0, cancel.stdout

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repair",
            "task",
            "--task",
            "resume-task",
            "--reason",
            "Inspect recovery options.",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "recorded repair inspection for task-0001" in result.stdout
    assert (
        "warning: Recorded a repair inspection event only; no task state was changed."
        in result.stdout
    )
    assert (
        "recovery: taskledger task uncancel "
        '--reason "Restore the task to a safe durable stage."' in result.stdout
    )


def test_task_first_support_commands_are_available(tmp_path: Path) -> None:
    _init_project(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "task",
                "create",
                "support-task",
                "--description",
                "Exercise task-first support commands.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(tmp_path), "task", "activate", "support-task"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "todo",
                "add",
                "--text",
                "write docs",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(tmp_path),
                "file",
                "add",
                "--path",
                "README.md",
                "--kind",
                "doc",
            ],
        ).exit_code
        == 0
    )

    todo_show = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "todo", "show", "todo-0001"],
    )
    assert _json(todo_show)["result"]["todo"]["id"] == "todo-0001"

    file_list = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "file", "list"],
    )
    assert file_list.exit_code == 0
    assert "@README.md [doc]" in file_list.stdout


def test_root_alias_uses_stable_json_envelope(tmp_path: Path) -> None:
    init_result = runner.invoke(app, ["--root", str(tmp_path), "init"])
    assert init_result.exit_code == 0

    create_result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--json",
            "task",
            "create",
            "root-alias-task",
            "--description",
            "Exercise the root alias.",
        ],
    )
    payload = _json(create_result)
    assert payload["command"] == "task.create"
    assert payload["result"]["slug"] == "root-alias-task"


def test_plan_approval_blocks_open_questions_with_json_error(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "question-blocked",
            "--description",
            "Approval should fail while a question is open.",
        ],
    )
    runner.invoke(
        app, ["--cwd", str(tmp_path), "plan", "start", "--task", "question-blocked"]
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "question",
            "add",
            "--text",
            "Need one more decision?",
            "--task",
            "question-blocked",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "plan",
            "propose",
            "--task",
            "question-blocked",
            "--text",
            "## Goal\n\nAnswer the question first.\n",
        ],
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "approve",
            "--task",
            "question-blocked",
            "--version",
            "1",
        ],
    )
    assert result.exit_code == 3
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "plan.approve"
    assert payload["error"]["code"] == "WORKFLOW_REJECTION"


def test_expired_lock_requires_explicit_break_json_error(tmp_path: Path) -> None:
    _init_project(tmp_path)
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "task",
            "create",
            "stale-lock-task",
            "--description",
            "Expired locks must be broken explicitly.",
        ],
    )
    runner.invoke(
        app, ["--cwd", str(tmp_path), "plan", "start", "--task", "stale-lock-task"]
    )

    lock_path = tmp_path / ".taskledger" / "tasks" / "task-0001" / "lock.yaml"
    payload = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    payload["expires_at"] = "2000-01-01T00:00:00+00:00"
    lock_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "plan",
            "propose",
            "--task",
            "stale-lock-task",
            "--text",
            "## Goal\n\nDo not silently replace stale locks.\n",
        ],
    )
    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "STALE_LOCK_REQUIRES_BREAK"


def test_context_for_implementer_todo_renders_focused_context(tmp_path: Path) -> None:
    _prepare_focused_context_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "context",
            "--for",
            "implementer",
            "--todo",
            "todo-0001",
            "--format",
            "markdown",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Implementation Context" in result.stdout
    assert "## Worker Role" in result.stdout
    assert "role: implementer" in result.stdout
    assert "scope: todo" in result.stdout
    assert "focused_todo: todo-0001" in result.stdout
    assert "## Focused Todo" in result.stdout
    assert "todo-0001" in result.stdout
    assert "[ ] todo-0001" not in result.stdout


def test_context_for_spec_reviewer_run_renders_review_context(tmp_path: Path) -> None:
    run_id = _prepare_focused_context_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "context",
            "--for",
            "spec-reviewer",
            "--run",
            run_id,
            "--format",
            "markdown",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Review Context" in result.stdout
    assert "role: spec-reviewer" in result.stdout
    assert "scope: run" in result.stdout
    assert f"focused_run: {run_id}" in result.stdout
    assert "## Spec Compliance Review" in result.stdout
    assert "acceptance_criteria_findings" in result.stdout
    assert "deviations_from_plan" in result.stdout


def test_context_for_code_reviewer_run_renders_review_context(tmp_path: Path) -> None:
    run_id = _prepare_focused_context_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "context",
            "--for",
            "code-reviewer",
            "--run",
            run_id,
            "--format",
            "markdown",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Review Context" in result.stdout
    assert "role: code-reviewer" in result.stdout
    assert "scope: run" in result.stdout
    assert f"focused_run: {run_id}" in result.stdout
    assert "## Code Quality Review" in result.stdout
    assert "maintainability" in result.stdout
    assert "test_coverage_gaps" in result.stdout


def test_handoff_create_and_show_focused_todo_snapshot(tmp_path: Path) -> None:
    _prepare_focused_context_task(tmp_path)

    create_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "handoff",
            "create",
            "--mode",
            "implementation",
            "--todo",
            "todo-0001",
        ],
    )
    payload = _json(create_result)
    assert payload["result"]["mode"] == "implementation"
    assert payload["result"]["context_for"] == "implementer"
    assert payload["result"]["scope"] == "todo"
    assert payload["result"]["todo_id"] == "todo-0001"
    assert str(payload["result"]["context_hash"]).startswith("sha256:")

    show_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "handoff",
            "show",
            "handoff-0001",
            "--format",
            "markdown",
        ],
    )
    assert show_result.exit_code == 0, show_result.stdout
    assert "Implementation Context" in show_result.stdout
    assert "## Worker Role" in show_result.stdout
    assert "## Focused Todo" in show_result.stdout
    assert "todo-0001" in show_result.stdout
