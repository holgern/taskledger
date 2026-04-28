from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from taskledger.domain.models import (
    PlanRecord,
    QuestionRecord,
    RequirementCollection,
    TaskLock,
    TaskRecord,
    TaskRunRecord,
    TaskTodo,
    TodoCollection,
    ValidationCheck,
)
from taskledger.domain.policies import derive_active_stage
from taskledger.services.navigation import (
    _answered_question_next_item,
    _commands_for_next_item,
    _compact_next_action_blockers,
    _plan_next_item,
    _primary_command_for_next_item,
    _question_next_item,
    _required_open_question_ids,
    _stale_answer_question_ids,
    _task_next_item,
    _todo_next_item,
    _validation_progress,
)
from taskledger.storage.events import load_recent_events
from taskledger.storage.locks import lock_is_expired
from taskledger.storage.paths import resolve_project_paths
from taskledger.storage.task_store import (
    list_changes,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    load_active_task_state,
    load_requirements,
    load_todos,
    read_lock,
    resolve_task,
    resolve_task_or_active,
    resolve_v2_paths,
    task_lock_path,
)

_LOCK_STAGE_TO_ACTIVE_STAGE = {
    "planning": "planning",
    "implementing": "implementation",
    "validating": "validation",
}


@dataclass(slots=True, frozen=True)
class ServeReadOptions:
    include_events: bool = False
    event_limit: int = 50
    include_all_plans: bool = True
    include_changes: bool = True
    include_validation: bool = True


_DEFAULT_SERVE_READ_OPTIONS = ServeReadOptions()


@dataclass(slots=True, frozen=True)
class TaskDashboardSnapshot:
    task: TaskRecord
    lock: TaskLock | None
    plans: list[PlanRecord]
    questions: list[QuestionRecord]
    runs: list[TaskRunRecord]
    changes: list[dict[str, object]]
    todos: TodoCollection
    requirements: RequirementCollection


def serve_project_summary(workspace_root: Path) -> dict[str, object]:
    paths = resolve_project_paths(workspace_root)
    active_task = None
    active_state = load_active_task_state(workspace_root)
    if active_state is not None:
        task = resolve_task(workspace_root, active_state.task_id)
        active_task = {
            "task_id": task.id,
            "slug": task.slug,
            "title": task.title,
            "status_stage": task.status_stage,
        }
    return {
        "kind": "serve_project",
        "workspace_root": str(paths.workspace_root),
        "config_path": str(paths.config_path),
        "taskledger_dir": str(paths.taskledger_dir),
        "project_dir": str(paths.project_dir),
        "active_task": active_task,
        "health": "not_checked",
    }


def serve_task_summaries(workspace_root: Path) -> dict[str, object]:
    tasks = list_tasks(workspace_root)
    active_locks = {
        lock.task_id: lock
        for lock in load_active_locks(workspace_root)
        if not lock_is_expired(lock)
    }
    return {
        "kind": "tasks",
        "tasks": [
            {
                "id": task.id,
                "slug": task.slug,
                "title": task.title,
                "status": task.status_stage,
                "status_stage": task.status_stage,
                "active_stage": (
                    _LOCK_STAGE_TO_ACTIVE_STAGE.get(active_locks[task.id].stage)
                    if task.id in active_locks
                    else None
                ),
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "description_summary": task.description_summary,
                "priority": task.priority,
                "labels": list(task.labels),
                "owner": task.owner,
                "accepted_plan_version": task.accepted_plan_version,
                "latest_plan_version": task.latest_plan_version,
            }
            for task in tasks
        ],
    }


def serve_dashboard_snapshot(
    workspace_root: Path,
    *,
    ref: str | None,
    options: ServeReadOptions | None = None,
) -> dict[str, object]:
    options = options or _DEFAULT_SERVE_READ_OPTIONS
    snapshot = _load_task_dashboard_snapshot(workspace_root, ref=ref)
    active_stage = _snapshot_active_stage(snapshot)
    todo_items = list(snapshot.todos.todos)
    payload: dict[str, object] = {
        "kind": "dashboard",
        "task": {
            "id": snapshot.task.id,
            "slug": snapshot.task.slug,
            "title": snapshot.task.title,
            "status_stage": snapshot.task.status_stage,
            "active_stage": active_stage,
            "created_at": snapshot.task.created_at,
            "updated_at": snapshot.task.updated_at,
            "description_summary": snapshot.task.description_summary,
            "priority": snapshot.task.priority,
            "labels": list(snapshot.task.labels),
            "owner": snapshot.task.owner,
        },
        "plan": _plan_summary(snapshot.plans),
        "plans": (
            [plan.to_dict() for plan in snapshot.plans]
            if options.include_all_plans
            else ([snapshot.plans[-1].to_dict()] if snapshot.plans else [])
        ),
        "next_action": _build_next_action_from_snapshot(workspace_root, snapshot),
        "questions": {
            "total": len(snapshot.questions),
            "open": sum(
                1 for question in snapshot.questions if question.status == "open"
            ),
            "items": [question.to_dict() for question in snapshot.questions],
        },
        "todos": {
            "total": len(todo_items),
            "done": sum(1 for todo in todo_items if todo.done),
            "items": [todo.to_dict() for todo in todo_items],
        },
        "files": {
            "total": len(snapshot.task.file_links),
            "links": [file_link.to_dict() for file_link in snapshot.task.file_links],
        },
        "runs": [run.to_dict() for run in snapshot.runs],
        "changes": snapshot.changes if options.include_changes else [],
        "lock": snapshot.lock.to_dict() if snapshot.lock is not None else None,
    }
    if options.include_validation:
        payload["validation"] = _build_validation_gate_report_from_snapshot(
            workspace_root, snapshot
        )
    if options.include_events:
        payload["events"] = serve_task_events(
            workspace_root,
            ref=snapshot.task.id,
            limit=options.event_limit,
        )
    return payload


def serve_task_events(
    workspace_root: Path,
    *,
    ref: str | None,
    limit: int,
) -> dict[str, object]:
    task = resolve_task_or_active(workspace_root, ref)
    events = load_recent_events(
        resolve_v2_paths(workspace_root).events_dir,
        task_id=task.id,
        limit=limit,
    )
    return {
        "kind": "events",
        "task_id": task.id,
        "items": [event.to_dict() for event in events],
    }


def _load_task_dashboard_snapshot(
    workspace_root: Path,
    *,
    ref: str | None,
) -> TaskDashboardSnapshot:
    task = resolve_task_or_active(workspace_root, ref)
    paths = resolve_v2_paths(workspace_root)
    return TaskDashboardSnapshot(
        task=task,
        lock=read_lock(task_lock_path(paths, task.id)),
        plans=list_plans(workspace_root, task.id),
        questions=list_questions(workspace_root, task.id),
        runs=list_runs(workspace_root, task.id),
        changes=[change.to_dict() for change in list_changes(workspace_root, task.id)],
        todos=load_todos(workspace_root, task.id),
        requirements=load_requirements(workspace_root, task.id),
    )


def _snapshot_active_stage(snapshot: TaskDashboardSnapshot) -> str | None:
    if snapshot.lock is None or lock_is_expired(snapshot.lock):
        return None
    return derive_active_stage(snapshot.lock, snapshot.runs)


def _latest_plan(snapshot: TaskDashboardSnapshot) -> PlanRecord | None:
    return snapshot.plans[-1] if snapshot.plans else None


def _accepted_plan(snapshot: TaskDashboardSnapshot) -> PlanRecord | None:
    if snapshot.task.accepted_plan_version is None:
        return None
    for plan in snapshot.plans:
        if plan.plan_version == snapshot.task.accepted_plan_version:
            return plan
    return None


def _plan_summary(plans: list[PlanRecord]) -> dict[str, object] | None:
    if not plans:
        return None
    latest = plans[-1]
    return {
        "version": latest.plan_version,
        "status": latest.status,
        "criteria": [criterion.to_dict() for criterion in latest.criteria],
        "body": latest.body,
    }


def _build_next_action_from_snapshot(
    workspace_root: Path,
    snapshot: TaskDashboardSnapshot,
) -> dict[str, object]:
    task = snapshot.task
    active_stage = _snapshot_active_stage(snapshot)
    action: str
    reason: str
    blockers: list[dict[str, object]] = []
    next_item: dict[str, object] | None = None
    progress: dict[str, object] = {}
    latest_plan = _latest_plan(snapshot)

    if active_stage == "planning":
        open_questions = _required_open_question_ids(snapshot.questions)
        answered_questions = [
            item.id
            for item in snapshot.questions
            if item.status == "answered" and item.required_for_plan
        ]
        stale_answers = (
            _stale_answer_question_ids(snapshot.questions, latest_plan)
            if latest_plan is not None
            else answered_questions
        )
        if open_questions:
            action, reason = "question-answer", "Required planning questions are open."
            question = _first_question_by_ids(snapshot.questions, open_questions)
            next_item = _question_next_item(question) if question is not None else None
            progress["questions"] = {
                "required_open": len(open_questions),
                "required_open_ids": open_questions,
            }
            blockers.append(
                {
                    "kind": "open_questions",
                    "question_ids": open_questions,
                    "message": "Required planning questions must be answered.",
                }
            )
        elif stale_answers:
            action, reason = (
                "plan-regenerate",
                "Answered planning questions should be reflected in the plan.",
            )
            question = _first_question_by_ids(snapshot.questions, stale_answers)
            next_item = (
                _answered_question_next_item(question) if question is not None else None
            )
            progress["questions"] = {
                "required_open": 0,
                "required_open_ids": [],
                "answered_since_latest_plan": stale_answers,
            }
        else:
            action, reason = (
                "plan-propose",
                "Planning is active; propose the next plan.",
            )
    elif active_stage == "implementation":
        todo_report = _todo_gate_report(snapshot)
        open_todo_ids = cast(list[str], todo_report.get("open_todos", []))
        progress["todos"] = {
            "total": todo_report["total"],
            "done": todo_report["done"],
            "open": len(open_todo_ids),
            "open_ids": open_todo_ids,
        }
        if open_todo_ids:
            todo = _first_open_todo(snapshot, open_todo_ids)
            next_item = _todo_next_item(todo) if todo is not None else None
            action, reason = (
                "todo-work",
                f"Implementation is in progress; {len(open_todo_ids)} todos remain.",
            )
        else:
            action, reason = (
                "implement-finish",
                "All todos done; ready to finish implementation.",
            )
            next_item = _task_next_item(task)
    elif active_stage == "validation":
        gate_report = _build_validation_gate_report_from_snapshot(
            workspace_root, snapshot
        )
        report_blockers = cast(list[dict[str, object]], gate_report.get("blockers", []))
        blockers.extend(_compact_next_action_blockers(report_blockers))
        progress["validation"] = _validation_progress(gate_report)
        if report_blockers:
            action, reason = (
                "validate-check",
                "Validation is in progress; required checks remain.",
            )
            next_item = _next_validation_item(snapshot, gate_report, report_blockers)
        else:
            action, reason = (
                "validate-finish",
                "Validation is complete enough to finish.",
            )
            next_item = _task_next_item(task)
    elif task.status_stage == "draft":
        action, reason = "plan", "Draft tasks need planning before work starts."
    elif task.status_stage == "plan_review":
        open_questions = _required_open_question_ids(snapshot.questions)
        stale_answers = (
            _stale_answer_question_ids(snapshot.questions, latest_plan)
            if latest_plan is not None
            else []
        )
        if open_questions:
            action, reason = "question-answer", "Required planning questions are open."
            question = _first_question_by_ids(snapshot.questions, open_questions)
            next_item = _question_next_item(question) if question is not None else None
            progress["questions"] = {
                "required_open": len(open_questions),
                "required_open_ids": open_questions,
            }
            blockers.append(
                {
                    "kind": "open_questions",
                    "question_ids": open_questions,
                    "message": "Required planning questions must be answered.",
                }
            )
        elif stale_answers:
            action, reason = (
                "plan-regenerate",
                "Answered planning questions are not reflected in the latest plan.",
            )
            question = _first_question_by_ids(snapshot.questions, stale_answers)
            next_item = (
                _answered_question_next_item(question) if question is not None else None
            )
            progress["questions"] = {
                "required_open": 0,
                "required_open_ids": [],
                "answered_since_latest_plan": stale_answers,
            }
            blockers.append(
                {
                    "kind": "stale_answers",
                    "question_ids": stale_answers,
                    "message": "Regenerate the plan from answered questions.",
                }
            )
        else:
            action, reason = "plan-approve", "A proposed plan is waiting for review."
            if latest_plan is not None:
                next_item = _plan_next_item(latest_plan)
    elif task.status_stage == "approved":
        action, reason = "implement", "The approved plan is ready for implementation."
        next_item = _task_next_item(task)
        if task.accepted_plan_version is None:
            blockers.append(
                {"kind": "approval", "message": "No accepted plan version is recorded."}
            )
        blockers.extend(_dependency_blockers_from_snapshot(workspace_root, snapshot))
    elif task.status_stage == "implemented":
        action, reason = "validate", "Implementation is complete and ready to validate."
        next_item = _task_next_item(task)
        implementation_run = _find_run(snapshot.runs, task.latest_implementation_run)
        if (
            implementation_run is None
            or implementation_run.run_type != "implementation"
            or implementation_run.status != "finished"
        ):
            blockers.append(
                {
                    "kind": "implementation",
                    "message": "Validation requires a finished implementation run.",
                }
            )
    elif task.status_stage == "failed_validation":
        action, reason = (
            "implement-restart",
            "Validation failed; restart implementation.",
        )
        next_item = _task_next_item(task)
        blockers.extend(_dependency_blockers_from_snapshot(workspace_root, snapshot))
    elif task.status_stage == "done":
        action, reason = "none", "The task is complete."
    else:
        action, reason = "none", "The task is cancelled."

    if snapshot.lock is not None and active_stage is None:
        blockers.append(
            {
                "kind": "lock",
                "message": (
                    f"Task has a {snapshot.lock.stage} lock from "
                    f"{snapshot.lock.run_id} without a matching running run."
                ),
            }
        )
        action = "repair-lock"
        reason = "A stale or broken lock must be repaired before work can continue."
        next_item = {
            "kind": "lock",
            "id": snapshot.lock.lock_id,
            "task_id": task.id,
            "stage": snapshot.lock.stage,
            "run_id": snapshot.lock.run_id,
            "expired": lock_is_expired(snapshot.lock),
        }

    next_command = _primary_command_for_next_item(action, next_item)
    return {
        "kind": "task_next_action",
        "task_id": task.id,
        "status_stage": task.status_stage,
        "active_stage": active_stage,
        "action": action,
        "reason": reason,
        "blocking": blockers,
        "next_command": next_command,
        "next_item": next_item,
        "commands": _commands_for_next_item(action, next_item),
        "progress": progress,
    }


def _todo_gate_report(snapshot: TaskDashboardSnapshot) -> dict[str, object]:
    open_todos = [
        todo.id
        for todo in snapshot.todos.todos
        if not todo.done
        and todo.status not in {"done", "skipped"}
        and (
            not todo.mandatory
            or todo.active_at is not None
            or todo.source == "plan"
            or todo.source_plan_id is not None
        )
    ]
    return {
        "kind": "todo_gate_report",
        "task_id": snapshot.task.id,
        "total": len(snapshot.todos.todos),
        "done": len(snapshot.todos.todos) - len(open_todos),
        "open_todos": open_todos,
        "blockers": [
            {
                "kind": "todo_open",
                "ref": todo_id,
                "message": f"Todo {todo_id} is not done.",
                "command_hint": f'taskledger todo done {todo_id} --evidence "..."',
            }
            for todo_id in open_todos
        ],
        "can_finish_implementation": not open_todos,
    }


def _first_open_todo(
    snapshot: TaskDashboardSnapshot,
    open_ids: list[str],
) -> TaskTodo | None:
    wanted = set(open_ids)
    for todo in snapshot.todos.todos:
        if todo.id in wanted and todo.status == "active" and not todo.done:
            return todo
    for todo in snapshot.todos.todos:
        if todo.id in wanted and not todo.done:
            return todo
    return None


def _build_validation_gate_report_from_snapshot(
    workspace_root: Path,
    snapshot: TaskDashboardSnapshot,
) -> dict[str, object]:
    task = snapshot.task
    run = _find_run(snapshot.runs, task.latest_validation_run)
    implementation_run = _find_run(snapshot.runs, task.latest_implementation_run)
    accepted_plan = _accepted_plan(snapshot)
    report: dict[str, Any] = {
        "kind": "validation_status",
        "task_id": task.id,
        "task_slug": task.slug,
        "status_stage": task.status_stage,
        "active_stage": None,
        "run_id": run.run_id if run is not None else None,
        "can_finish_passed": False,
        "accepted_plan": {},
        "implementation": {},
        "criteria": [],
    }

    if accepted_plan is not None:
        report["accepted_plan"] = {
            "version": accepted_plan.plan_version,
            "status": accepted_plan.status,
        }

    if implementation_run is not None:
        report["implementation"] = {
            "run_id": implementation_run.run_id,
            "status": implementation_run.status,
            "satisfied": implementation_run.status == "finished",
        }

    missing_criteria: list[str] = []
    failing_criteria: list[str] = []
    checks_by_criterion: dict[str, list[ValidationCheck]] = {}
    if run is not None:
        for check in run.checks:
            if check.criterion_id is not None:
                checks_by_criterion.setdefault(check.criterion_id, []).append(check)

    if accepted_plan is not None:
        for criterion in accepted_plan.criteria:
            checks = checks_by_criterion.get(criterion.id, [])
            latest_check = checks[-1] if checks else None
            latest_status = (
                latest_check.status if latest_check is not None else "not_run"
            )
            has_waiver = (
                latest_check is not None
                and latest_check.waiver is not None
                and latest_check.waiver.actor.actor_type == "user"
            )
            satisfied = latest_status == "pass" or has_waiver
            criterion_blockers: list[dict[str, str]] = []
            if criterion.mandatory:
                if latest_status == "fail":
                    criterion_blockers.append(
                        {"kind": "criterion_fail", "message": "Latest check failed"}
                    )
                    failing_criteria.append(criterion.id)
                elif latest_status == "not_run":
                    criterion_blockers.append(
                        {
                            "kind": "criterion_missing",
                            "message": "No passing check recorded",
                        }
                    )
                    missing_criteria.append(criterion.id)
                elif not satisfied:
                    criterion_blockers.append(
                        {
                            "kind": "criterion_unsatisfied",
                            "message": f"Latest check status: {latest_status}",
                        }
                    )
                    missing_criteria.append(criterion.id)
            cast(list[dict[str, object]], report["criteria"]).append(
                {
                    "id": criterion.id,
                    "text": criterion.text,
                    "mandatory": criterion.mandatory,
                    "latest_check_id": (
                        latest_check.id if latest_check is not None else None
                    ),
                    "latest_status": latest_status,
                    "satisfied": satisfied,
                    "has_waiver": has_waiver,
                    "evidence": list(latest_check.evidence) if latest_check else [],
                    "history": [
                        {"check_id": check.id, "status": check.status}
                        for check in checks
                    ],
                    "blockers": criterion_blockers,
                }
            )

    open_todos = [
        todo.id for todo in snapshot.todos.todos if todo.mandatory and not todo.done
    ]
    dependency_blockers = _dependency_blockers_from_snapshot(workspace_root, snapshot)

    blockers: list[dict[str, object]] = []
    if accepted_plan is None:
        blockers.append(
            {
                "kind": "no_accepted_plan",
                "message": "No accepted plan is recorded.",
                "command_hint": (
                    "taskledger plan propose ... && taskledger plan approve ..."
                ),
            }
        )
    elif accepted_plan.status != "accepted":
        blockers.append(
            {
                "kind": "plan_not_accepted",
                "message": (
                    "Accepted plan record status is "
                    f"{accepted_plan.status}, not accepted."
                ),
            }
        )

    if implementation_run is None or implementation_run.status != "finished":
        blockers.append(
            {
                "kind": "no_finished_implementation",
                "message": "No finished implementation run is recorded.",
                "command_hint": (
                    "taskledger implement start ... && taskledger implement finish ..."
                ),
            }
        )

    for criterion_id in missing_criteria:
        blockers.append(
            {
                "kind": "criterion_missing",
                "ref": criterion_id,
                "message": f"Mandatory criterion {criterion_id} has no passing check.",
                "command_hint": (
                    "taskledger validate check "
                    f"--criterion {criterion_id} --status pass "
                    '--evidence "..."'
                ),
            }
        )
    for criterion_id in failing_criteria:
        blockers.append(
            {
                "kind": "criterion_fail",
                "ref": criterion_id,
                "message": f"Mandatory criterion {criterion_id} has a failing check.",
                "command_hint": (
                    "taskledger validate check "
                    f"--criterion {criterion_id} --status pass "
                    '--evidence "..."'
                ),
            }
        )
    for todo_id in open_todos:
        blockers.append(
            {
                "kind": "todo_open",
                "ref": todo_id,
                "message": f"Mandatory todo {todo_id} is not done.",
                "command_hint": f'taskledger todo done {todo_id} --evidence "..."',
            }
        )
    for blocker in dependency_blockers:
        blockers.append(
            {
                "kind": "dependency_blocker",
                "ref": blocker["ref"],
                "message": blocker["message"],
            }
        )

    report["todos"] = {"open_mandatory": open_todos}
    report["dependencies"] = {"blockers": dependency_blockers}
    report["blockers"] = blockers
    report["can_finish_passed"] = not blockers
    return report


def _dependency_blockers_from_snapshot(
    workspace_root: Path,
    snapshot: TaskDashboardSnapshot,
) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for requirement in snapshot.requirements.requirements:
        if (
            requirement.waiver is not None
            and requirement.waiver.actor.actor_type == "user"
        ):
            continue
        required = resolve_task(workspace_root, requirement.task_id)
        if required.status_stage != "done":
            blockers.append(
                {
                    "kind": "dependency",
                    "ref": required.id,
                    "message": (
                        f"Requirement {required.id} is still {required.status_stage}."
                    ),
                }
            )
    return blockers


def _find_run(
    runs: list[TaskRunRecord],
    run_id: str | None,
) -> TaskRunRecord | None:
    if run_id is None:
        return None
    for run in runs:
        if run.run_id == run_id:
            return run
    return None


def _first_question_by_ids(
    questions: list[QuestionRecord],
    ids: list[str],
) -> QuestionRecord | None:
    wanted = set(ids)
    for question in questions:
        if question.id in wanted:
            return question
    return None


def _criterion_report_by_id(
    gate_report: dict[str, object],
    criterion_id: str,
) -> dict[str, object] | None:
    for criterion in cast(list[dict[str, object]], gate_report.get("criteria", [])):
        if criterion.get("id") == criterion_id:
            return criterion
    return None


def _next_validation_item(
    snapshot: TaskDashboardSnapshot,
    gate_report: dict[str, object],
    blockers: list[dict[str, object]],
) -> dict[str, object] | None:
    priority = (
        "criterion_fail",
        "criterion_missing",
        "criterion_unsatisfied",
        "todo_open",
        "no_finished_implementation",
        "dependency_blocker",
        "no_accepted_plan",
        "plan_not_accepted",
    )
    for kind in priority:
        for blocker in blockers:
            if blocker.get("kind") != kind:
                continue
            ref = blocker.get("ref")
            if kind.startswith("criterion_") and isinstance(ref, str):
                criterion = _criterion_report_by_id(gate_report, ref)
                if criterion is not None:
                    return {
                        "kind": "criterion",
                        "id": criterion.get("id"),
                        "text": criterion.get("text"),
                        "mandatory": criterion.get("mandatory"),
                        "latest_status": criterion.get("latest_status"),
                        "satisfied": criterion.get("satisfied"),
                    }
            if kind == "todo_open" and isinstance(ref, str):
                todo = _first_open_todo(snapshot, [ref])
                if todo is not None:
                    return _todo_next_item(todo)
            if kind == "dependency_blocker" and isinstance(ref, str):
                return {"kind": "dependency", "id": ref}
            if kind == "no_finished_implementation":
                return _task_next_item(snapshot.task)
            if kind in {"no_accepted_plan", "plan_not_accepted"}:
                latest_plan = _latest_plan(snapshot)
                if latest_plan is not None:
                    return _plan_next_item(latest_plan)
                return _task_next_item(snapshot.task)

    for criterion in cast(list[dict[str, object]], gate_report.get("criteria", [])):
        if criterion.get("blockers"):
            return {
                "kind": "criterion",
                "id": criterion.get("id"),
                "text": criterion.get("text"),
                "mandatory": criterion.get("mandatory"),
                "latest_status": criterion.get("latest_status"),
                "satisfied": criterion.get("satisfied"),
            }
    return None


__all__ = [
    "ServeReadOptions",
    "TaskDashboardSnapshot",
    "serve_dashboard_snapshot",
    "serve_project_summary",
    "serve_task_events",
    "serve_task_summaries",
]
