from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.api.runtime_support import save_run_record
from taskledger.api.types import RunRecord
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
