from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from taskledger.api.items import (
    approve_item,
    create_item,
    update_item,
    write_item_memory_body,
)
from taskledger.api.memories import create_memory
from taskledger.api.project import init_project
from taskledger.api.runtime_support import save_run_record
from taskledger.api.types import RunRecord
from taskledger.api.validation import append_validation_record
from taskledger.api.workflows import mark_stage_succeeded
from taskledger.cli import app


def _make_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


runner = _make_runner()


def test_cli_composite_commands_cover_item_run_and_context_workflows(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = _prepare_implement_item(tmp_path)
    _save_run(
        tmp_path,
        run_id="run-1",
        project_item_ref=item.id,
        stage="implementation",
        final_message="Implemented tests",
    )

    summary_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "item", "summary", item.slug],
    )
    prompt_result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "--json", "item", "work-prompt", item.slug],
    )
    start_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "start",
            item.slug,
            "--mark-running",
        ],
    )
    apply_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "run",
            "apply",
            "run-1",
            "--mark-stage-succeeded",
            "--summary",
            "Implemented tests",
        ],
    )
    append_validation_record(
        tmp_path,
        project_item_ref=item.id,
        memory_ref=json.loads(apply_result.stdout)["applied"]["promoted_memory_ref"],
        kind="pytest",
        status="passed",
        run_id="run-1",
        notes="pytest passed",
    )
    complete_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "complete-stage",
            item.slug,
            "--stage",
            "validate_summary",
            "--summary",
            "Validation summarized",
        ],
    )
    context_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "context",
            "build-for-item",
            item.slug,
            "--save-as",
            "working-set",
        ],
    )
    refine_result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "--json",
            "item",
            "refine",
            item.slug,
            "--description",
            "Sharper description",
            "--acceptance",
            "Pytest passes",
            "--validation-check",
            "pytest",
        ],
    )

    summary_payload = json.loads(summary_result.stdout)
    prompt_payload = json.loads(prompt_result.stdout)
    start_payload = json.loads(start_result.stdout)
    apply_payload = json.loads(apply_result.stdout)
    complete_payload = json.loads(complete_result.stdout)
    context_payload = json.loads(context_result.stdout)
    refine_payload = json.loads(refine_result.stdout)

    assert summary_result.exit_code == 0
    assert summary_payload["item"]["slug"] == item.slug
    assert prompt_result.exit_code == 0
    assert prompt_payload["stage"] == "implement"
    assert start_result.exit_code == 0
    assert start_payload["workflow"]["marked_running"] is True
    assert apply_result.exit_code == 0
    assert apply_payload["applied"]["attached_to_role"] == "implementation"
    assert apply_payload["item"]["stage"] == "validate"
    assert complete_result.exit_code == 0
    assert complete_payload["completed_stage"] == "validate_summary"
    assert complete_payload["workflow"]["current_stage"] is None
    assert context_result.exit_code == 0
    assert context_payload["context"]["name"] == "working-set"
    assert refine_result.exit_code == 0
    assert refine_payload["item"]["description"] == "Sharper description"


def _prepare_implement_item(tmp_path: Path):
    item = create_item(
        tmp_path,
        slug="increase-coverage",
        description="Run pytest and improve the weakest file.",
        repo_refs=("taskledger",),
        target_repo_ref="taskledger",
    )
    write_item_memory_body(
        tmp_path,
        item.id,
        "analysis",
        "Coverage report shows storage/memories.py is weakest.",
    )
    write_item_memory_body(tmp_path, item.id, "plan", "1. Add tests for edge cases.")
    update_item(tmp_path, item.id, add_acceptance=("Coverage does not regress",))
    approve_item(tmp_path, item.id)
    mark_stage_succeeded(tmp_path, item.id, "plan", summary="Plan complete")
    save_target = create_memory(tmp_path, name=f"{item.slug} save-target")
    update_item(tmp_path, item.id, save_target_ref=save_target.id)
    return item


def _save_run(
    workspace_root: Path,
    *,
    run_id: str,
    project_item_ref: str,
    stage: str,
    final_message: str,
) -> RunRecord:
    run_dir = workspace_root / ".taskledger" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(
        json.dumps({"final_message": final_message}) + "\n",
        encoding="utf-8",
    )
    record = RunRecord(
        run_id=run_id,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        memory_inputs=(),
        file_inputs=(),
        item_inputs=(project_item_ref,),
        inline_inputs=(),
        context_inputs=(),
        loop_artifact_inputs=(),
        save_target=None,
        save_mode=None,
        stage=stage,
        repo_refs=("taskledger",),
        context_hash="hash",
        status="succeeded",
        result_path=f".taskledger/runs/{run_id}/result.json",
        preview_path=f".taskledger/runs/{run_id}/preview.json",
        prompt_path=f".taskledger/runs/{run_id}/prompt.txt",
        composed_prompt_path=f".taskledger/runs/{run_id}/composed_prompt.txt",
        report_path=None,
        project_item_ref=project_item_ref,
    )
    save_run_record(workspace_root, record)
    return record
