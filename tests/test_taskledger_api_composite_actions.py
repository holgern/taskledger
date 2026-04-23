from __future__ import annotations

import json
from pathlib import Path

from taskledger.api.contexts import build_context_for_item, show_context_entry
from taskledger.api.items import (
    approve_item,
    build_item_work_prompt,
    complete_item_stage,
    create_item,
    item_summary,
    refine_item,
    start_item_work,
    update_item,
    write_item_memory_body,
)
from taskledger.api.memories import create_memory
from taskledger.api.project import init_project
from taskledger.api.runs import apply_run_result
from taskledger.api.runtime_support import save_run_record
from taskledger.api.types import RunRecord
from taskledger.api.validation import append_validation_record
from taskledger.api.workflows import mark_stage_succeeded


def test_item_summary_and_work_prompt_use_compact_machine_payloads(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = _prepare_implement_item(tmp_path)
    validation_memory = write_item_memory_body(
        tmp_path,
        item.id,
        "validation",
        "pytest passed",
    )
    _save_run(
        tmp_path,
        run_id="run-1",
        project_item_ref=item.id,
        stage="implementation",
        final_message="Implemented the missing tests",
    )
    append_validation_record(
        tmp_path,
        project_item_ref=item.id,
        memory_ref=validation_memory.id,
        kind="pytest",
        status="passed",
        notes="pytest passed",
    )

    by_slug = item_summary(tmp_path, item.slug)
    by_id = item_summary(tmp_path, item.id)
    prompt = build_item_work_prompt(tmp_path, item.id)

    assert by_slug["item"]["id"] == item.id
    assert by_id["item"]["slug"] == item.slug
    assert by_slug["next_action"]["kind"] == "work_stage"
    assert by_slug["next_action"]["stage"] == "implement"
    assert by_slug["memories"]["analysis"]["excerpt"].startswith("Coverage report")
    assert by_slug["recent_runs"][0]["id"] == "run-1"
    assert by_slug["validation_records"][0]["id"] == "val-1"
    assert prompt["stage"] == "implement"
    assert prompt["target_repo_ref"] == "taskledger"
    assert prompt["save_target_ref"] == "mem-3"
    assert "implement" in prompt["prompt"].lower()
    assert "taskledger" in prompt["prompt"]


def test_start_item_work_marks_stage_running_when_requested(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = _prepare_implement_item(tmp_path)

    payload = start_item_work(tmp_path, item.slug, mark_running=True)

    assert payload["item"]["id"] == item.id
    assert payload["workflow"]["current_stage"] == "implement"
    assert payload["workflow"]["marked_running"] is True
    assert "Work on Taskledger item" in payload["prompt"]


def test_complete_item_stage_and_refine_item_return_updated_summaries(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = _prepare_implement_item(tmp_path)
    _save_run(
        tmp_path,
        run_id="run-2",
        project_item_ref=item.id,
        stage="implementation",
        final_message="Implemented tests",
    )

    completed = complete_item_stage(
        tmp_path,
        item.id,
        stage_id="implement",
        run_refs=("run-2",),
        summary="Implemented tests",
    )
    refined = refine_item(
        tmp_path,
        item.id,
        description="Improved description",
        acceptance_criteria=("Pytest passes",),
        validation_checks=("pytest",),
        repo_refs=("taskledger",),
        target_repo_ref="taskledger",
    )

    assert completed["completed_stage"] == "implement"
    assert completed["attached_run_refs"] == ["run-2"]
    assert completed["workflow"]["current_stage"] == "validate"
    assert refined["updated_fields"] == [
        "description",
        "acceptance_criteria",
        "validation_checks",
    ]
    assert refined["item"]["description"] == "Improved description"
    assert refined["acceptance_criteria"] == ["Pytest passes"]
    assert refined["validation_checks"] == ["pytest"]


def test_apply_run_result_and_build_context_for_item_cover_run_and_context_flows(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = _prepare_implement_item(tmp_path, with_implementation_memory=False)
    run = _save_run(
        tmp_path,
        run_id="run-3",
        project_item_ref=item.id,
        stage="implementation",
        final_message="Implemented the feature",
        report_text="Validation report",
    )

    applied = apply_run_result(
        tmp_path,
        run.run_id,
        mode="output",
        mark_stage_succeeded=True,
        summary="Implemented the feature",
    )
    append_validation_record(
        tmp_path,
        project_item_ref=item.id,
        memory_ref=applied["applied"]["promoted_memory_ref"],
        kind="pytest",
        status="passed",
        run_id=run.run_id,
        notes="pytest passed",
    )
    context_payload = build_context_for_item(tmp_path, item.id, save_as="working-set")
    context_entry = show_context_entry(tmp_path, "working-set")

    assert applied["run"]["id"] == "run-3"
    assert applied["applied"]["attached_to_role"] == "implementation"
    assert applied["item"]["stage"] == "validate"
    assert context_payload["context"]["name"] == "working-set"
    assert context_payload["sources"]["item_refs"] == [item.id]
    assert context_payload["sources"]["run_refs"] == ["run-3"]
    assert context_payload["sources"]["validation_refs"] == ["val-1"]
    assert context_payload["bundle_summary"]["source_count"] >= 1
    assert context_entry.item_refs == (item.id,)
    assert any("Work on Taskledger item" in text for text in context_entry.inline_texts)


def _prepare_implement_item(
    tmp_path: Path,
    *,
    with_implementation_memory: bool = False,
):
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
    if with_implementation_memory:
        write_item_memory_body(
            tmp_path,
            item.id,
            "implementation",
            "Implementation notes and saved output target.",
        )
    return item


def _save_run(
    workspace_root: Path,
    *,
    run_id: str,
    project_item_ref: str,
    stage: str,
    final_message: str,
    report_text: str | None = None,
) -> RunRecord:
    run_dir = workspace_root / ".taskledger" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(
        json.dumps({"final_message": final_message}) + "\n",
        encoding="utf-8",
    )
    report_path = None
    if report_text is not None:
        report_path = run_dir / "report.md"
        report_path.write_text(report_text, encoding="utf-8")
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
        report_path=(f".taskledger/runs/{run_id}/report.md" if report_path else None),
        project_item_ref=project_item_ref,
    )
    save_run_record(workspace_root, record)
    return record
