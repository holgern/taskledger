from __future__ import annotations

from pathlib import Path

from taskledger.api.items import next_action_payload
from taskledger.api.runs import summarize_run_inventory
from taskledger.api.validation import summarize_validation_records
from taskledger.doctor import inspect_project
from taskledger.exchange import (
    export_project_payload,
    import_project_payload,
    parse_project_import_payload,
    write_project_snapshot,
)
from taskledger.models import ProjectState
from taskledger.storage import (
    ensure_project_exists,
    init_project_state,
    load_project_state,
    load_validation_records,
    resolve_taskledger_root,
)
from taskledger.workflow import build_workflow_summary, choose_next_workflow_item


def init_project(workspace_root: Path) -> dict[str, object]:
    paths, created = init_project_state(workspace_root)
    return {
        "kind": "taskledger_init",
        "root": str(paths.project_dir),
        "created": created,
        "canonical_root": str(resolve_taskledger_root(workspace_root)),
    }


def project_status_summary(workspace_root: Path) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=None)
    doctor = inspect_project(workspace_root)
    validation_records = load_validation_records(state.paths)
    return {
        "kind": "taskledger_status",
        "counts": _project_counts(state, validation_records=validation_records),
        "healthy": bool(doctor["healthy"]),
    }


def project_status(workspace_root: Path) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=None)
    doctor = inspect_project(workspace_root)
    next_step = project_next(workspace_root)
    validation_records = load_validation_records(state.paths)
    workflow = build_workflow_summary(state)
    return {
        "kind": "taskledger_status",
        "project_dir": str(state.paths.project_dir),
        "canonical_root": str(resolve_taskledger_root(workspace_root)),
        "counts": _project_counts(state, validation_records=validation_records),
        "run_inventory": summarize_run_inventory(workspace_root),
        "validation_summary": summarize_validation_records(workspace_root),
        "workflow": workflow,
        "healthy": bool(doctor["healthy"]),
        "warnings": list(doctor["warnings"]),
        "errors": list(doctor["errors"]),
        "next": next_step,
    }


def project_board(workspace_root: Path) -> dict[str, object]:
    state = load_project_state(workspace_root, recent_runs_limit=None)
    return {
        "kind": "taskledger_board",
        "project_dir": str(state.paths.project_dir),
        "work_items": {
            "by_status": _group_work_items_by_status(state),
            "open": [
                _work_item_summary(item)
                for item in state.work_items
                if item.status != "closed"
            ],
        },
    }


def project_next(workspace_root: Path) -> dict[str, object] | None:
    state = load_project_state(workspace_root, recent_runs_limit=None)
    workflow_item = choose_next_workflow_item(state)
    if workflow_item is not None:
        item_ref = workflow_item.get("item_ref")
        selected = next(
            (item for item in state.work_items if item.id == item_ref),
            None,
        )
        if selected is not None:
            workflow_schema = _workflow_schema(state)
            workflow_status = workflow_item.get("workflow_status")
            if workflow_status in {"blocked", "waiting_validation"}:
                blocked_by = workflow_item.get("blocked_by")
                blockers = ", ".join(blocked_by) if isinstance(blocked_by, list) else ""
                payload = {
                    "kind": "project_item_next",
                    "item_ref": selected.id,
                    "action": "unblock",
                    "actor": "human_or_runtime",
                    "reason": (
                        "Workflow dependencies are blocking progress."
                        + (f" Blocked by: {blockers}." if blockers else "")
                    ),
                    "workflow_artifact": workflow_item.get("next_artifact"),
                    "blocked_by": blocked_by,
                }
                if workflow_schema is not None:
                    payload["workflow_schema"] = workflow_schema
                return payload
            if workflow_status == "waiting_approval":
                payload = {
                    "kind": "project_item_next",
                    "item_ref": selected.id,
                    "action": "approve",
                    "actor": "human",
                    "reason": (
                        "Workflow approval is required before the next stage can start."
                    ),
                    "workflow_artifact": workflow_item.get("next_artifact"),
                    "blocked_by": workflow_item.get("blocked_by"),
                }
                if workflow_schema is not None:
                    payload["workflow_schema"] = workflow_schema
                return payload
            next_step = next_action_payload(selected)
            workflow_artifact = workflow_item.get("next_artifact")
            if isinstance(workflow_artifact, str):
                next_step["workflow_artifact"] = workflow_artifact
                next_step["action"] = workflow_artifact
                next_step["actor"] = "runtime"
                next_step["workflow_status"] = workflow_item.get("next_artifact_status")
                next_step["reason"] = (
                    f"Workflow artifact {workflow_artifact} is ready. "
                    f"{next_step['reason']}"
                )
            if workflow_schema is not None:
                next_step["workflow_schema"] = workflow_schema
            return next_step
    for status in (
        "draft",
        "planned",
        "approved",
        "in_progress",
        "implemented",
        "validated",
    ):
        for item in state.work_items:
            if item.status == status:
                return next_action_payload(item)
    return None


def project_report(workspace_root: Path) -> dict[str, object]:
    status = project_status(workspace_root)
    board = project_board(workspace_root)
    return {
        "kind": "taskledger_report",
        "status": status,
        "board": board,
        "doctor": inspect_project(workspace_root),
    }


def project_doctor(workspace_root: Path) -> dict[str, object]:
    ensure_project_exists(workspace_root)
    return inspect_project(workspace_root)


def project_export(
    workspace_root: Path,
    *,
    include_bodies: bool = False,
    include_run_artifacts: bool = False,
) -> dict[str, object]:
    return export_project_payload(
        workspace_root,
        include_bodies=include_bodies,
        include_run_artifacts=include_run_artifacts,
    )


def project_import(
    workspace_root: Path,
    *,
    text: str,
    format_name: str = "json",
    replace: bool = False,
) -> dict[str, object]:
    payload = parse_project_import_payload(text, format_name=format_name)
    return import_project_payload(workspace_root, payload=payload, replace=replace)


def project_snapshot(
    workspace_root: Path,
    *,
    output_dir: Path,
    include_bodies: bool = False,
    include_run_artifacts: bool = False,
) -> dict[str, object]:
    return write_project_snapshot(
        workspace_root,
        output_dir=output_dir,
        include_bodies=include_bodies,
        include_run_artifacts=include_run_artifacts,
    )


def _project_counts(
    state: ProjectState, *, validation_records: list[dict[str, object]]
) -> dict[str, int]:
    return {
        "repos": len(state.repos),
        "memories": len(state.memories),
        "contexts": len(state.contexts),
        "work_items": len(state.work_items),
        "runs": len(state.recent_runs),
        "validation_records": len(validation_records),
    }


def _group_work_items_by_status(state: ProjectState) -> dict[str, int]:
    grouped: dict[str, int] = {}
    for item in state.work_items:
        grouped[item.status] = grouped.get(item.status, 0) + 1
    return grouped


def _work_item_summary(item) -> dict[str, object]:
    return {
        "id": item.id,
        "slug": item.slug,
        "title": item.title,
        "status": item.status,
        "stage": item.stage,
    }


def _workflow_schema(state: ProjectState) -> str | None:
    workflow = build_workflow_summary(state)
    if workflow is None:
        return None
    schema = workflow.get("schema")
    return schema if isinstance(schema, str) else None
