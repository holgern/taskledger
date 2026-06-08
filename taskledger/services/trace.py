from __future__ import annotations

from pathlib import Path
from typing import Any

from taskledger.services.validation import build_validation_gate_report
from taskledger.storage.task_store import (
    list_changes,
    list_code_reviews,
    list_handoffs,
    list_plans,
    list_runs,
    load_bdd_examples,
    load_bdd_reports,
    load_links,
    resolve_task,
)

ARCHLEDGER_LINK_ROLES = {
    "archledger-record",
    "adr",
    "architecture-decision",
    "architecture-requirement",
    "quality-scenario",
    "runtime-scenario",
}


def build_task_trace(workspace_root: Path, task_ref: str) -> dict[str, Any]:
    """Build a read-only task-centered combo trace bundle."""
    task = resolve_task(workspace_root, task_ref)
    plans = list_plans(workspace_root, task.id)
    accepted_plan = next(
        (plan for plan in plans if plan.plan_version == task.accepted_plan_version),
        None,
    )
    bdd_examples = load_bdd_examples(workspace_root, task.id)
    bdd_reports = load_bdd_reports(workspace_root, task.id)
    links = load_links(workspace_root, task.id).links
    runs = list_runs(workspace_root, task.id)
    changes = list_changes(workspace_root, task.id)
    reviews = list_code_reviews(workspace_root, task.id)
    handoffs = list_handoffs(workspace_root, task.id)

    ac_ids = sorted(c.id for c in accepted_plan.criteria) if accepted_plan else []
    bdd_ids = sorted(example.id for example in bdd_examples)
    source_refs = sorted({change.path for change in changes if change.path})
    test_refs = sorted(
        {
            ref
            for example in bdd_examples
            for ref in (
                example.automation.pytest_nodeid,
                example.automation.pytest_path,
            )
            if ref
        }
    )
    feature_refs = sorted(
        {
            example.automation.feature_file
            for example in bdd_examples
            if example.automation.feature_file
        }
    )
    evidence_refs = sorted(
        {
            ref
            for report in bdd_reports
            for ref in (
                report.id,
                report.source_path,
                *report.validation_check_refs,
            )
            if ref
        }
    )
    archledger_refs = sorted(
        {
            ref
            for ref in (
                *(
                    link.path
                    for link in links
                    if (link.target_type or link.kind) in ARCHLEDGER_LINK_ROLES
                ),
                *(ref for example in bdd_examples for ref in example.archledger_refs),
            )
            if ref
        }
    )

    validation = build_validation_gate_report(workspace_root, task)
    gaps: list[dict[str, str]] = []
    if not bdd_examples:
        gaps.append(
            {
                "kind": "missing_behavior_mapping",
                "message": "No task-local BDD examples recorded.",
            }
        )
    linked_bdd = [example for example in bdd_examples if example.acceptance_criteria]
    if bdd_examples and not linked_bdd:
        gaps.append(
            {
                "kind": "unlinked_bdd",
                "message": "BDD examples have no acceptance-criterion links.",
            }
        )
    if linked_bdd and not bdd_reports:
        gaps.append(
            {
                "kind": "missing_evidence",
                "message": "Linked BDD examples have no imported evidence report.",
            }
        )

    return {
        "schema": "combi.trace.v1",
        "producer": "taskledger",
        "subject": {"type": "task", "id": task.id},
        "task_ids": [task.id],
        "ac_ids": ac_ids,
        "bdd_ids": bdd_ids,
        "archledger_refs": archledger_refs,
        "source_refs": sorted(set(source_refs + feature_refs)),
        "test_refs": test_refs,
        "evidence_refs": evidence_refs,
        "status": {
            "task": task.status_stage,
            "active_stage": None,
            "plan": accepted_plan.status if accepted_plan else None,
            "validation": validation,
            "runs": {run.run_id: run.status for run in runs},
            "bdd_reports": {report.id: report.result for report in bdd_reports},
            "changes": [change.change_id for change in changes],
            "reviews": [review.review_id for review in reviews],
            "handoffs": [handoff.handoff_id for handoff in handoffs],
        },
        "gaps": gaps,
    }
