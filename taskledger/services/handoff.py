from __future__ import annotations

from typing import cast
from pathlib import Path

from taskledger.domain.models import TaskRunRecord
from taskledger.domain.policies import derive_active_stage
from taskledger.errors import LaunchError
from taskledger.storage.locks import lock_is_expired, lock_status, read_lock
from taskledger.storage.v2 import (
    list_changes,
    list_plans,
    list_questions,
    list_runs,
    load_links,
    load_requirements,
    load_todos,
    resolve_introduction,
    resolve_plan,
    resolve_task,
    resolve_v2_paths,
    task_lock_path,
)


def render_handoff(
    workspace_root: Path,
    task_ref: str,
    *,
    mode: str,
    format_name: str = "markdown",
) -> str | dict[str, object]:
    mode = _canonical_mode(mode)
    payload = build_handoff_payload(workspace_root, task_ref, mode=mode)
    if format_name == "json":
        return payload
    if format_name not in {"markdown", "text"}:
        raise LaunchError(f"Unsupported handoff format: {format_name}")
    return render_markdown_handoff(payload)


def build_handoff_payload(
    workspace_root: Path,
    task_ref: str,
    *,
    mode: str,
) -> dict[str, object]:
    mode = _canonical_mode(mode)
    task = resolve_task(workspace_root, task_ref)
    intro = (
        resolve_introduction(workspace_root, task.introduction_ref)
        if task.introduction_ref
        else None
    )
    plans = list_plans(workspace_root, task.id)
    questions = list_questions(workspace_root, task.id)
    runs = list_runs(workspace_root, task.id)
    changes = list_changes(workspace_root, task.id)
    accepted_plan = (
        resolve_plan(workspace_root, task.id, version=task.accepted_plan_version)
        if task.accepted_plan_version is not None
        else None
    )
    latest_impl = _latest_run(runs, "implementation")
    latest_validation = _latest_run(runs, "validation")
    lock = read_lock(task_lock_path(resolve_v2_paths(workspace_root), task.id))
    active_stage = (
        None
        if lock is None or lock_is_expired(lock)
        else derive_active_stage(lock, runs)
    )

    dependencies = []
    for requirement in (
        item.task_id for item in load_requirements(workspace_root, task.id).requirements
    ):
        dependency = resolve_task(workspace_root, requirement)
        dependencies.append(
            {
                "task_id": dependency.id,
                "title": dependency.title,
                "status_stage": dependency.status_stage,
            }
        )

    open_questions = [item.to_dict() for item in questions if item.status == "open"]
    answered_questions = [
        item.to_dict() for item in questions if item.status == "answered"
    ]
    dismissed_questions = [
        item.to_dict() for item in questions if item.status == "dismissed"
    ]
    validation_history = [
        run.to_dict()
        for run in runs
        if run.run_type == "validation" and run.status != "running"
    ]
    
    validation_status_report = None
    if mode in {"validation", "full"}:
        from taskledger.services.tasks import _build_validation_gate_report
        validation_status_report = _build_validation_gate_report(workspace_root, task)

    return {
        "kind": "task_handoff",
        "mode": mode,
        "task": {**task.to_dict(), "active_stage": active_stage},
        "introduction": intro.to_dict() if intro is not None else None,
        "guardrails": _guardrails_for_mode(mode),
        "accepted_plan": accepted_plan.to_dict() if accepted_plan is not None else None,
        "plans": [plan.to_dict() for plan in plans],
        "questions": {
            "open": open_questions,
            "answered": answered_questions,
            "dismissed": dismissed_questions,
        },
        "todos": [todo.to_dict() for todo in load_todos(workspace_root, task.id).todos],
        "file_links": [
            item.to_dict() for item in load_links(workspace_root, task.id).links
        ],
        "dependencies": dependencies,
        "runs": {
            "latest_planning": _run_to_dict(_latest_run(runs, "planning")),
            "latest_implementation": _run_to_dict(latest_impl),
            "latest_validation": _run_to_dict(latest_validation),
        },
        "lock": lock.to_dict() if lock is not None else None,
        "lock_status": lock_status(lock),
        "changes": [change.to_dict() for change in changes],
        "validation_history": validation_history,
        "validation_status": validation_status_report,
    }


def render_markdown_handoff(payload: dict[str, object]) -> str:
    mode = str(payload["mode"])
    task = payload["task"]
    assert isinstance(task, dict)
    title_prefix = {
        "planning": "Planning Context",
        "implementation": "Implementation Context",
        "validation": "Validation Context",
        "review": "Review Context",
        "full": "Task Dossier",
    }.get(mode, "Task Context")
    lines = [f"# {title_prefix}: {task['title']}", ""]
    _append_task_section(lines, task)
    _append_description(lines, task)
    _append_intro(lines, payload.get("introduction"))
    _append_dependencies(lines, payload["dependencies"])
    _append_file_links(lines, payload["file_links"])
    _append_plans(lines, payload["plans"])
    _append_questions(lines, payload["questions"])
    _append_guardrails(lines, payload["guardrails"])
    if mode in {"full", "implementation", "validation", "review"}:
        _append_accepted_plan(lines, payload.get("accepted_plan"))
    if mode in {"full", "implementation"}:
        _append_todos(lines, payload["todos"])
        _append_lock_and_runs(lines, payload)
    if mode in {"full", "validation"}:
        _append_implementation_summary(lines, payload["runs"])
        _append_change_log(lines, payload["changes"])
        _append_todos(lines, payload["todos"])
        _append_validation_status(lines, payload.get("validation_status"))
        _append_validation_history(lines, payload["validation_history"])
    _append_required_output(lines, mode)
    return "\n".join(lines).rstrip() + "\n"


def _append_task_section(lines: list[str], task: dict[str, object]) -> None:
    lines.extend(
        [
            "## Task",
            "",
            f"- id: {task['id']}",
            f"- slug: {task['slug']}",
            f"- status_stage: {task['status_stage']}",
            f"- active_stage: {task.get('active_stage') or 'none'}",
            f"- priority: {task.get('priority') or 'unset'}",
            f"- labels: {', '.join(cast(list[str], task.get('labels') or [])) or 'none'}",
            f"- owner: {task.get('owner') or 'unassigned'}",
            "",
        ]
    )


def _append_description(lines: list[str], task: dict[str, object]) -> None:
    lines.extend(["## Description", "", str(task.get("body") or ""), ""])


def _append_intro(lines: list[str], intro: object) -> None:
    if not isinstance(intro, dict):
        return
    lines.extend(["## Introduction", "", str(intro.get("body") or ""), ""])


def _append_dependencies(lines: list[str], dependencies: object) -> None:
    if not isinstance(dependencies, list):
        return
    lines.extend(["## Requirements", ""])
    for item in dependencies:
        if isinstance(item, dict):
            lines.append(
                f"- {item['task_id']}: {item['title']} — {item['status_stage']}"
            )
    if not dependencies:
        lines.append("- none")
    lines.append("")


def _append_file_links(lines: list[str], file_links: object) -> None:
    if not isinstance(file_links, list):
        return
    lines.extend(["## Linked Files", ""])
    for item in file_links:
        if isinstance(item, dict):
            lines.append(f"- @{item['path']} [{item['kind']}]")
    if not file_links:
        lines.append("- none")
    lines.append("")


def _append_plans(lines: list[str], plans: object) -> None:
    if not isinstance(plans, list):
        return
    lines.extend(["## Existing Plans", ""])
    for item in plans:
        if isinstance(item, dict):
            lines.append(f"- v{item['plan_version']} {item['status']}")
    if not plans:
        lines.append("- none")
    lines.append("")


def _append_questions(lines: list[str], payload: object) -> None:
    if not isinstance(payload, dict):
        return
    lines.extend(["## Questions", "", "### Open", ""])
    open_items = payload.get("open")
    if isinstance(open_items, list) and open_items:
        for item in open_items:
            if isinstance(item, dict):
                lines.append(f"- {item['id']}: {item['question']}")
    else:
        lines.append("- none")
    lines.extend(["", "### Answered", ""])
    answered_items = payload.get("answered")
    if isinstance(answered_items, list) and answered_items:
        for item in answered_items:
            if isinstance(item, dict):
                lines.append(
                    f"- {item['question']} -> {item.get('answer') or '(none)'}"
                )
    else:
        lines.append("- none")
    lines.append("")


def _append_guardrails(lines: list[str], guardrails: object) -> None:
    if not isinstance(guardrails, list):
        return
    lines.extend(["## Guardrails", ""])
    for item in guardrails:
        lines.append(f"- {item}")
    lines.append("")


def _append_accepted_plan(lines: list[str], accepted_plan: object) -> None:
    if not isinstance(accepted_plan, dict):
        return
    lines.extend(["## Accepted Plan", "", str(accepted_plan.get("body") or ""), ""])


def _append_todos(lines: list[str], todos: object) -> None:
    if not isinstance(todos, list):
        return
    lines.extend(["## Todo Checklist", ""])
    for item in todos:
        if isinstance(item, dict):
            mark = "x" if item.get("done") else " "
            lines.append(f"- [{mark}] {item['id']}: {item['text']}")
    if not todos:
        lines.append("- none")
    lines.append("")


def _append_lock_and_runs(lines: list[str], payload: dict[str, object]) -> None:
    lines.extend(["## Current Run / Lock State", ""])
    runs = payload["runs"]
    assert isinstance(runs, dict)
    latest_impl = runs.get("latest_implementation")
    if isinstance(latest_impl, dict):
        lines.append(
            f"- implementation run: {latest_impl['run_id']} ({latest_impl['status']})"
        )
    else:
        lines.append("- implementation run: none")
    status = payload.get("lock_status")
    if isinstance(status, dict) and status.get("active"):
        lines.append(
            
                f"- lock: {status.get('stage')} / {status.get('run_id')} "
                f"expired={status.get('expired')}"
            
        )
    else:
        lines.append("- lock: none")
    lines.append("")


def _append_implementation_summary(lines: list[str], runs: object) -> None:
    if not isinstance(runs, dict):
        return
    latest_impl = runs.get("latest_implementation")
    lines.extend(["## Implementation Summary", ""])
    if isinstance(latest_impl, dict):
        lines.append(str(latest_impl.get("summary") or "(no summary)"))
    else:
        lines.append("(no implementation run)")
    lines.append("")


def _append_change_log(lines: list[str], changes: object) -> None:
    if not isinstance(changes, list):
        return
    lines.extend(["## Code Changes", ""])
    for item in changes:
        if isinstance(item, dict):
            lines.append(f"- @{item['path']}: {item['summary']}")
    if not changes:
        lines.append("- none")
    lines.append("")




def _append_validation_status(lines: list[str], status: object) -> None:
    """Append validation status report to handoff markdown."""
    if not isinstance(status, dict):
        return
    
    lines.append("## Current Validation Status")
    lines.append("")
    
    can_finish = status.get("can_finish_passed", False)
    status_stage = status.get("status_stage", "unknown")
    lines.append(f"**Task Stage:** {status_stage}")
    lines.append(f"**Can Finish Passed:** {'✓ Yes' if can_finish else '✗ No'}")
    lines.append("")
    
    criteria = status.get("criteria", [])
    if criteria:
        lines.append("### Acceptance Criteria")
        for criterion in criteria:
            if isinstance(criterion, dict):
                criterion_id = criterion.get("id", "?")
                mandatory = criterion.get("mandatory", False)
                satisfied = criterion.get("satisfied", False)
                latest_status = criterion.get("latest_status", "unknown")
                has_waiver = criterion.get("has_waiver", False)
                text = criterion.get("text", "")
                
                checkbox = "[x]" if satisfied else "[ ]"
                mandatory_marker = " (mandatory)" if mandatory else ""
                lines.append(f"  {checkbox} **{criterion_id}**{mandatory_marker}")
                if text:
                    lines.append(f"      {text}")
                lines.append(f"      Status: {latest_status}")
                if has_waiver:
                    lines.append(f"      ✓ Waived by user")
        lines.append("")
    
    todos_obj = status.get("todos", {})
    if isinstance(todos_obj, dict):
        open_todos = todos_obj.get("open_mandatory", [])
        if open_todos:
            lines.append("### Open Mandatory Todos")
            for todo_id in open_todos:
                lines.append(f"  - [ ] {todo_id}")
            lines.append("")
    
    dependencies_obj = status.get("dependencies", {})
    if isinstance(dependencies_obj, dict):
        dep_blockers = dependencies_obj.get("blockers", [])
        if dep_blockers:
            lines.append("### Dependency Blockers")
            for blocker_id in dep_blockers:
                lines.append(f"  - {blocker_id}")
            lines.append("")
    
    if not can_finish:
        blockers = status.get("blockers", [])
        if blockers:
            lines.append("### Blocking Issues")
            for blocker in blockers:
                if isinstance(blocker, dict):
                    kind = blocker.get("kind", "unknown")
                    message = blocker.get("message", "")
                    lines.append(f"  - **[{kind}]** {message}")
            lines.append("")


def _append_validation_history(lines: list[str], history: object) -> None:
    if not isinstance(history, list):
        return
    lines.extend(["## Previous Validation History", ""])
    for item in history:
        if isinstance(item, dict):
            lines.append(
                
                    f"- {item['run_id']}: "
                    f"{item.get('result') or item['status']} — "
                    f"{item.get('summary') or ''}"
                
            )
    if not history:
        lines.append("- none")
    lines.append("")


def _append_validation_status(lines: list[str], status_report: object) -> None:
    """Append current validation status to handoff before required output section."""
    if not isinstance(status_report, dict):
        return
    
    lines.extend(["## Validation Status", ""])
    
    can_finish = status_report.get("can_finish_passed", False)
    lines.append(f"**Can Finish Passed:** {'✓ Yes' if can_finish else '✗ No'}")
    lines.append("")
    
    criteria = status_report.get("criteria", [])
    if criteria and isinstance(criteria, list):
        lines.append("### Acceptance Criteria")
        for criterion in criteria:
            if isinstance(criterion, dict):
                criterion_id = criterion.get("id", "unknown")
                mandatory = criterion.get("mandatory", False)
                satisfied = criterion.get("satisfied", False)
                latest_status = criterion.get("latest_status", "unknown")
                
                checkbox = "☒" if satisfied else "☐"
                mandatory_marker = " (mandatory)" if mandatory else ""
                lines.append(f"- {checkbox} {criterion_id}{mandatory_marker}: {latest_status}")
        lines.append("")
    
    blockers = status_report.get("blockers", [])
    if blockers and isinstance(blockers, list) and not can_finish:
        lines.append("### Blocking Issues")
        for blocker in blockers:
            if isinstance(blocker, dict):
                kind = blocker.get("kind", "unknown")
                message = blocker.get("message", "")
                lines.append(f"- [{kind}] {message}")
        lines.append("")



def _append_required_output(lines: list[str], mode: str) -> None:
    section = {
        "planning": [
            "plan body",
            "assumptions",
            "risks",
            "acceptance criteria",
            "open questions",
        ],
        "implementation": [
            "worklog entries",
            "code change records",
            "todo updates",
            "implementation summary",
        ],
        "validation": [
            "structured checks",
            "evidence",
            "summary",
            "recommendation",
        ],
        "review": ["approval decision"],
        "full": ["next action"],
    }[mode]
    lines.extend(["## Required Output", ""])
    for item in section:
        lines.append(f"- {item}")
    lines.append("")


def _guardrails_for_mode(mode: str) -> list[str]:
    if mode == "planning":
        return [
            "Produce a reviewable plan body.",
            "Call out assumptions and risks explicitly.",
            "Do not start implementation in this context.",
        ]
    if mode == "implementation":
        return [
            "Implement only the accepted plan.",
            "Log deviations explicitly.",
            "Log every code change.",
            "Do not validate in this context.",
        ]
    if mode == "validation":
        return [
            "Validate against the accepted plan and implementation log.",
            "Store failed validation; do not hide it.",
            "Report deviations from plan.",
        ]
    return ["Use this handoff as the source of truth for the next step."]


def _latest_run(runs: list[TaskRunRecord], run_type: str) -> TaskRunRecord | None:
    matches = [item for item in runs if item.run_type == run_type]
    return matches[-1] if matches else None


def _run_to_dict(run: TaskRunRecord | None) -> dict[str, object] | None:
    return run.to_dict() if run is not None else None


def _canonical_mode(mode: str) -> str:
    return {
        "plan-context": "planning",
        "implementation-context": "implementation",
        "validation-context": "validation",
        "show": "full",
    }.get(mode, mode)
