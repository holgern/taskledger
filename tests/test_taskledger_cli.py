from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from typer.testing import CliRunner

from taskledger.api.runtime_support import save_run_record
from taskledger.api.types import RunRecord
from taskledger.api.workflows import resolve_workflow
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
    assert "plan_memory_ref" in item_show.stdout
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


def test_taskledger_context_commands_cover_rename_and_delete(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    save_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "context", "save", "Sprint Context"],
    )
    rename_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "context",
            "rename",
            "sprint-context",
            "--new-name",
            "Release Context",
        ],
    )
    delete_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "context", "delete", "release-context"],
    )
    list_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "context", "list"],
    )

    assert save_result.exit_code == 0
    assert rename_result.exit_code == 0
    assert '"slug": "release-context"' in rename_result.stdout
    assert delete_result.exit_code == 0
    assert "deleted context release-context" in delete_result.stdout
    assert list_result.exit_code == 0
    assert "(empty)" in list_result.stdout


def test_taskledger_memory_commands_cover_rename_retag_prepend_and_delete(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "memory",
            "create",
            "Notes",
            "--text",
            "world",
        ],
    )

    rename_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "memory",
            "rename",
            "notes",
            "--new-name",
            "Plan Notes",
        ],
    )
    retag_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "memory",
            "retag",
            "plan-notes",
            "--add-tag",
            "plan",
            "--add-tag",
            "draft",
        ],
    )
    prepend_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "memory",
            "prepend",
            "plan-notes",
            "--text",
            "hello",
        ],
    )
    delete_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "memory", "delete", "plan-notes"],
    )

    assert rename_result.exit_code == 0
    assert "renamed memory mem-0001" in rename_result.stdout
    assert retag_result.exit_code == 0
    assert '"tags": [' in retag_result.stdout
    assert '"plan"' in retag_result.stdout
    assert prepend_result.exit_code == 0
    assert '"body": "hello\\n\\nworld"' in prepend_result.stdout
    assert delete_result.exit_code == 0
    assert "deleted memory mem-0001" in delete_result.stdout


def test_taskledger_item_memory_role_access(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "plan-ux",
            "--text",
            "Track plan updates",
        ],
    )

    memories_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "item", "memories", "item-0001"],
    )
    show_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "memory",
            "show",
            "item-0001",
            "--role",
            "plan",
        ],
    )
    write_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "memory",
            "write",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "Step A",
        ],
    )
    append_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "memory",
            "append",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "Step B",
        ],
    )
    prepend_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "memory",
            "prepend",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "Step 0",
        ],
    )

    assert memories_result.exit_code == 0
    assert '"plan": "mem-0003"' in memories_result.stdout
    assert show_result.exit_code == 0
    assert '"body": ""' in show_result.stdout
    assert write_result.exit_code == 0
    assert '"body": "Step A"' in write_result.stdout
    assert append_result.exit_code == 0
    assert '"body": "Step A\\n\\nStep B"' in append_result.stdout
    assert prepend_result.exit_code == 0
    assert '"body": "Step 0\\n\\nStep A\\n\\nStep B"' in prepend_result.stdout


def test_taskledger_item_update_and_invalid_removals(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "item-update",
            "--text",
            "Original description",
        ],
    )

    update_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "update",
            "item-0001",
            "--title",
            "Updated title",
            "--text",
            "Updated description",
            "--notes",
            "Notes here",
            "--owner",
            "alice",
            "--estimate",
            "2d",
            "--add-label",
            "planning",
            "--add-dependency",
            "item-0099",
            "--add-repo",
            "backend",
            "--add-acceptance",
            "Tests pass",
            "--add-validation-check",
            "Run smoke suite",
            "--target-repo",
            "backend",
            "--save-target",
            "mem-0004",
        ],
    )
    remove_missing_label = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "update",
            "item-0001",
            "--remove-label",
            "missing",
        ],
    )

    assert update_result.exit_code == 0
    assert '"title": "Updated title"' in update_result.stdout
    assert '"description": "Updated description"' in update_result.stdout
    assert '"owner": "alice"' in update_result.stdout
    assert '"planning"' in update_result.stdout
    assert '"item-0099"' in update_result.stdout
    assert '"Run smoke suite"' in update_result.stdout
    assert remove_missing_label.exit_code == 1
    assert '"error": "Cannot remove unknown item label: missing"' in (
        remove_missing_label.stdout
    )


def test_taskledger_item_lifecycle_requires_plan_content(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "lifecycle-check",
            "--text",
            "Lifecycle behavior",
        ],
    )

    approve_empty = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "item", "approve", "item-0001"],
    )
    close_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "item", "close", "item-0001"],
    )
    reopen_draft = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "item", "reopen", "item-0001"],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "memory",
            "write",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "Plan is now present",
        ],
    )
    close_again = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "item", "close", "item-0001"],
    )
    reopen_planned = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "item", "reopen", "item-0001"],
    )

    assert approve_empty.exit_code == 1
    assert "cannot be approved without plan content" in approve_empty.stdout
    assert close_result.exit_code == 0
    assert reopen_draft.exit_code == 0
    assert '"status": "draft"' in reopen_draft.stdout
    assert close_again.exit_code == 0
    assert reopen_planned.exit_code == 0
    assert '"status": "planned"' in reopen_planned.stdout


def test_taskledger_repo_commands_cover_remove_role_and_default(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Main Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    role_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "set-role",
            "main-repo",
            "--role",
            "write",
        ],
    )
    default_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "repo", "set-default", "main-repo"],
    )
    clear_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "repo", "clear-default"],
    )
    remove_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "repo", "remove", "main-repo"],
    )

    assert role_result.exit_code == 0
    assert "role=write" in role_result.stdout
    assert default_result.exit_code == 0
    assert '"preferred_for_execution": true' in default_result.stdout
    assert clear_result.exit_code == 0
    assert "cleared default execution repo" in clear_result.stdout
    assert remove_result.exit_code == 0
    assert "removed repo Main Repo" in remove_result.stdout


def test_taskledger_runs_commands_cover_delete_cleanup_promote_and_summary(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    first_run = _create_run(
        tmp_path,
        run_id="run-0001",
        final_message="Saved output",
        report_text="Validation report",
    )
    second_run = _create_run(
        tmp_path,
        run_id="run-0002",
        final_message="Keep me",
    )

    promote_output = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "runs",
            "promote-output",
            first_run.run_id,
            "--name",
            "Run Output",
        ],
    )
    promote_report = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "runs",
            "promote-report",
            first_run.run_id,
            "--name",
            "Run Report",
        ],
    )
    summary_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "runs", "summary"],
    )
    cleanup_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "runs", "cleanup", "--keep", "1"],
    )
    delete_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "runs", "delete", second_run.run_id],
    )

    assert promote_output.exit_code == 0
    assert f"promoted run {first_run.run_id} output to memory" in promote_output.stdout
    assert promote_report.exit_code == 0
    assert '"memory"' in promote_report.stdout
    assert summary_result.exit_code == 0
    assert '"count": 2' in summary_result.stdout
    assert cleanup_result.exit_code == 0
    assert first_run.run_id in cleanup_result.stdout
    assert delete_result.exit_code == 0
    assert f"deleted run {second_run.run_id}" in delete_result.stdout


def test_taskledger_validation_commands_cover_add_list_remove_and_summary(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
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

    add_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "validation",
            "add",
            "--item",
            "item-0001",
            "--memory",
            "mem-0005",
            "--kind",
            "smoke",
            "--status",
            "passed",
            "--verdict",
            "ok",
            "--source",
            '{"tool":"pytest"}',
        ],
    )
    list_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "validation", "list"],
    )
    summary_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "validation", "summary"],
    )
    remove_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "validation", "remove", "--id", "val-0001"],
    )

    assert add_result.exit_code == 0
    assert '"id": "val-0001"' in add_result.stdout
    assert list_result.exit_code == 0
    assert "val-0001  smoke  passed  item-0001->mem-0005" in list_result.stdout
    assert summary_result.exit_code == 0
    assert '"count": 1' in summary_result.stdout
    assert remove_result.exit_code == 0
    assert "val-0001" in remove_result.stdout


def test_taskledger_exec_request_commands_cover_build_expand_and_outcome(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "exec-req",
            "--text",
            "Exercise execution request commands.",
        ],
    )
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "memory",
            "write",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "Prepared implementation plan",
        ],
    )
    runner.invoke(
        app,
        ["--cwd", str(tmp_path), "item", "approve", "item-0001"],
    )

    build_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "exec-request",
            "build",
            "item-0001",
            "implement",
            "--inline",
            "Context line",
        ],
    )
    assert build_result.exit_code == 0
    build_payload = json.loads(build_result.stdout)
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(build_payload) + "\n", encoding="utf-8")

    expand_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "exec-request",
            "expand",
            "--request-file",
            str(request_path),
        ],
    )
    record_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "exec-request",
            "record-outcome",
            "--request-file",
            str(request_path),
            "--ok",
            "--text",
            "Completed planning",
        ],
    )

    assert expand_result.exit_code == 0
    assert '"request": {' in expand_result.stdout
    assert '"stage_id": "implement"' in expand_result.stdout
    assert record_result.exit_code == 0
    assert '"status": "succeeded"' in record_result.stdout


def test_taskledger_compose_and_runtime_support_commands(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "compose-ops",
            "--text",
            "Exercise compose and runtime support commands.",
        ],
    )
    repo_dir = tmp_path / "runtime-repo"
    repo_dir.mkdir()
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "repo",
            "add",
            "Runtime Repo",
            "--path",
            str(repo_dir),
            "--role",
            "both",
        ],
    )

    compose_expand = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "compose",
            "expand",
            "--item",
            "item-0001",
            "--inline",
            "extra context",
        ],
    )
    compose_bundle = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "compose",
            "bundle",
            "--prompt",
            "Plan this work",
            "--item",
            "item-0001",
        ],
    )
    runtime_config = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "runtime-support", "config"],
    )
    runtime_layout = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "runtime-support",
            "run-layout",
            "--origin",
            "tests",
        ],
    )
    runtime_resolve = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "runtime-support",
            "resolve-repo",
            "runtime-repo",
        ],
    )

    assert compose_expand.exit_code == 0
    assert '"kind": "project_compose_expand"' in compose_expand.stdout
    assert compose_bundle.exit_code == 0
    assert '"kind": "project_compose"' in compose_bundle.stdout
    assert '"composed_prompt":' in compose_bundle.stdout
    assert runtime_config.exit_code == 0
    assert '"default_source_max_chars"' in runtime_config.stdout
    assert runtime_layout.exit_code == 0
    assert '"run_dir":' in runtime_layout.stdout
    assert runtime_resolve.exit_code == 0
    assert '"repo_ref": "runtime-repo"' in runtime_resolve.stdout


def test_taskledger_workflow_commands_cover_show_state_and_transitions(
    tmp_path: Path,
) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "workflow-fix",
            "--text",
            "Add workflow support.",
        ],
    )
    plan_write = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "memory",
            "write",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "1. Draft implementation tasks",
        ],
    )
    approve_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "item", "approve", "item-0001"],
    )

    show_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "workflow", "show", "default-item-v1"],
    )
    state_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "workflow", "state", "item-0001"],
    )
    transitions_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "workflow", "transitions", "item-0001"],
    )

    assert show_result.exit_code == 0
    assert plan_write.exit_code == 0
    assert approve_result.exit_code == 0
    assert "WORKFLOW default-item-v1" in show_result.stdout
    assert state_result.exit_code == 0
    assert '"workflow_id": "default-item-v1"' in state_result.stdout
    assert transitions_result.exit_code == 0
    assert "implement" in transitions_result.stdout


def test_taskledger_workflow_commands_cover_parity_contract(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "create",
            "workflow-contract",
            "--text",
            "Exercise workflow parity commands.",
        ],
    )
    plan_write = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "item",
            "memory",
            "write",
            "item-0001",
            "--role",
            "plan",
            "--text",
            "1. Gather requirements",
        ],
    )
    approve_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "item", "approve", "item-0001"],
    )

    base_workflow = resolve_workflow(tmp_path, "default-item-v1")
    custom_workflow = replace(
        base_workflow,
        workflow_id="custom-item-v2",
        name="Custom item workflow v2",
        default_for_items=False,
    )
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(custom_workflow.to_dict()) + "\n",
        encoding="utf-8",
    )

    save_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "save",
            "--from-file",
            str(workflow_path),
        ],
    )
    default_before = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "workflow", "default"],
    )
    set_default = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "workflow", "set-default", "custom-item-v2"],
    )
    assign_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "workflow", "assign", "item-0001", "custom-item-v2"],
    )
    can_enter = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "can-enter",
            "item-0001",
            "implement",
        ],
    )
    enter_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "workflow", "enter", "item-0001", "implement"],
    )
    mark_running = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "mark-running",
            "item-0001",
            "implement",
            "--request-id",
            "req-001",
        ],
    )
    mark_succeeded = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "mark-succeeded",
            "item-0001",
            "implement",
            "--run-id",
            "run-001",
            "--summary",
            "Completed planning",
            "--save-target",
            "mem-0001",
            "--validation-record",
            "val-0001",
        ],
    )
    latest_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "latest",
            "item-0001",
            "implement",
        ],
    )
    records_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "workflow", "records", "item-0001"],
    )
    mark_needs_review = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "mark-needs-review",
            "item-0001",
            "implement",
            "--reason",
            "Manual check requested",
        ],
    )
    mark_failed = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "mark-failed",
            "item-0001",
            "implement",
            "--summary",
            "Validation failed",
        ],
    )
    delete_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "workflow", "delete", "custom-item-v2"],
    )
    default_after = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "workflow", "default"],
    )

    assert plan_write.exit_code == 0
    assert approve_result.exit_code == 0
    assert save_result.exit_code == 0
    assert '"workflow_id": "custom-item-v2"' in save_result.stdout
    assert default_before.exit_code == 0
    assert '"workflow_id": "default-item-v1"' in default_before.stdout
    assert set_default.exit_code == 0
    assert '"default_for_items": true' in set_default.stdout
    assert assign_result.exit_code == 0
    assert "assigned workflow custom-item-v2 to item-0001" in assign_result.stdout
    assert can_enter.exit_code == 0
    assert '"allowed": true' in can_enter.stdout
    assert enter_result.exit_code == 0
    assert "entered workflow stage implement for item-0001" in enter_result.stdout
    assert mark_running.exit_code == 0
    assert '"status": "running"' in mark_running.stdout
    assert '"request_id": "req-001"' in mark_running.stdout
    assert mark_succeeded.exit_code == 0
    assert '"status": "succeeded"' in mark_succeeded.stdout
    assert '"run_id": "run-001"' in mark_succeeded.stdout
    assert latest_result.exit_code == 0
    assert '"stage_id": "implement"' in latest_result.stdout
    assert '"status": "succeeded"' in latest_result.stdout
    assert records_result.exit_code == 0
    assert '"record_id":' in records_result.stdout
    assert mark_needs_review.exit_code == 0
    assert '"status": "needs_review"' in mark_needs_review.stdout
    assert mark_failed.exit_code == 0
    assert '"status": "failed"' in mark_failed.stdout
    assert delete_result.exit_code == 0
    assert '"deleted": true' in delete_result.stdout
    assert default_after.exit_code == 0
    assert '"workflow_id": "default-item-v1"' in default_after.stdout


def test_taskledger_workflow_save_rejects_invalid_json(tmp_path: Path) -> None:
    runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    invalid_payload = tmp_path / "invalid-workflow.json"
    invalid_payload.write_text("{", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "workflow",
            "save",
            "--from-file",
            str(invalid_payload),
        ],
    )

    assert result.exit_code == 1
    assert '"error": "Workflow file must be valid JSON:' in result.stdout


def _create_run(
    workspace_root: Path,
    *,
    run_id: str,
    final_message: str,
    report_text: str | None = None,
) -> RunRecord:
    run_dir = workspace_root / ".taskledger" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps({"final_message": final_message}) + "\n",
        encoding="utf-8",
    )
    report_path = None
    if report_text is not None:
        report_path = run_dir / "report.md"
        report_path.write_text(report_text, encoding="utf-8")
    record = _run_record(run_id, report_path=report_path)
    save_run_record(workspace_root, record)
    return record


def _run_record(run_id: str, *, report_path: Path | None = None) -> RunRecord:
    base = f".taskledger/runs/{run_id}"
    return RunRecord(
        run_id=run_id,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        memory_inputs=(),
        file_inputs=(),
        item_inputs=(),
        inline_inputs=(),
        context_inputs=(),
        loop_artifact_inputs=(),
        save_target=None,
        save_mode=None,
        stage=None,
        repo_refs=(),
        context_hash="hash",
        status="succeeded",
        result_path=f"{base}/result.json",
        preview_path=f"{base}/preview.json",
        prompt_path=f"{base}/prompt.txt",
        composed_prompt_path=f"{base}/composed_prompt.txt",
        report_path=f"{base}/report.md" if report_path is not None else None,
    )
