from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from taskledger.api.execution_requests import (
    build_execution_request,
    expand_execution_request,
    record_execution_outcome,
)
from taskledger.api.items import approve_item, create_item, update_item
from taskledger.api.project import init_project, project_export, project_import
from taskledger.api.types import ExecutionOutcomeRecord, ExecutionStatus
from taskledger.api.workflows import (
    assign_item_workflow,
    enter_stage,
    item_stage_records,
    item_workflow_state,
    list_workflows,
    mark_stage_succeeded,
    resolve_workflow,
    save_workflow_definition,
)


def test_default_workflow_requires_approval_then_unblocks_plan(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="workflow-item", description="Workflow item")
    update_item(tmp_path, item.id, add_acceptance=("Acceptance exists",))

    initial = item_workflow_state(tmp_path, item.id)
    approved = approve_item(tmp_path, item.id)
    after_approval = item_workflow_state(tmp_path, approved.id)

    assert initial.workflow_id == "default-item-v1"
    assert initial.workflow_status == "waiting_approval"
    assert initial.pending_approvals == ("plan",)
    assert initial.allowed_next_stages == ()
    assert after_approval.workflow_status == "ready"
    assert after_approval.allowed_next_stages == ("plan",)


def test_execution_request_outcome_advances_to_next_stage(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="plan-stage", description="Plan the item")
    update_item(tmp_path, item.id, add_acceptance=("Acceptance exists",))
    approve_item(tmp_path, item.id)

    request = build_execution_request(
        tmp_path,
        item_ref=item.id,
        stage_id="plan",
        inline_texts=("Use the default workflow.",),
    )
    expanded = expand_execution_request(tmp_path, request=request)
    outcome = ExecutionOutcomeRecord(
        harness=None,
        status=ExecutionStatus.SUCCEEDED,
        prompt=expanded.final_prompt,
        cwd=None,
        command=(),
        returncode=0,
        pid=None,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        duration_seconds=0.1,
        completion_method="test",
        stdout="Plan complete",
        stderr=None,
        done_file=None,
        final_message="Plan complete",
    )

    record = record_execution_outcome(tmp_path, request=request, outcome=outcome)
    state = item_workflow_state(tmp_path, item.id)

    assert "Plan the item" in expanded.final_prompt
    assert record.status == "succeeded"
    assert state.allowed_next_stages == ("implement",)
    assert state.current_stage_id == "implement"


def test_export_import_round_trip_preserves_custom_workflow_and_stage_records(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="custom-wf", description="Uses a custom workflow")
    update_item(tmp_path, item.id, add_acceptance=("Acceptance exists",))
    approve_item(tmp_path, item.id)

    base_workflow = resolve_workflow(tmp_path, "default-item-v1")
    custom = save_workflow_definition(
        tmp_path,
        replace(
            base_workflow,
            workflow_id="custom-item-v1",
            name="Custom item workflow",
            default_for_items=False,
        ),
    )
    assign_item_workflow(tmp_path, item.id, custom.workflow_id)
    enter_stage(tmp_path, item.id, "plan")
    mark_stage_succeeded(tmp_path, item.id, "plan", summary="Saved plan")

    payload = project_export(tmp_path)

    imported_root = tmp_path / "imported"
    init_project(imported_root)
    project_import(imported_root, text=json.dumps(payload))

    imported_workflows = list_workflows(imported_root)
    imported_records = item_stage_records(imported_root, "item-0001")

    assert any(
        workflow.workflow_id == "custom-item-v1" for workflow in imported_workflows
    )
    assert len(imported_records) >= 2
