from __future__ import annotations

import difflib
import getpass
import os
import socket
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from taskledger.domain.models import (
    ActorRef,
    CodeChangeRecord,
    FileLink,
    IntroductionRecord,
    PlanRecord,
    QuestionRecord,
    TaskEvent,
    TaskLock,
    TaskRecord,
    TaskRunRecord,
    TaskTodo,
    ValidationCheck,
)
from taskledger.domain.policies import (
    implementation_mutation_decision,
    metadata_edit_decision,
    plan_approve_decision,
    plan_propose_decision,
    plan_revise_decision,
    question_add_decision,
    question_mutation_decision,
    require_known_actor_role,
    todo_add_decision,
    todo_toggle_decision,
    validation_check_decision,
)
from taskledger.domain.states import (
    ACTIVE_TASK_STAGES,
    EXIT_CODE_APPROVAL_REQUIRED,
    EXIT_CODE_BAD_INPUT,
    EXIT_CODE_DEPENDENCY_BLOCKED,
    EXIT_CODE_INVALID_TRANSITION,
    EXIT_CODE_LOCK_CONFLICT,
    EXIT_CODE_MISSING,
    IMPLEMENTABLE_TASK_STAGES,
    TaskStatusStage,
    normalize_file_link_kind,
    normalize_validation_check_status,
    normalize_validation_result,
    require_transition,
)
from taskledger.errors import LaunchError
from taskledger.ids import next_project_id, slugify_project_ref
from taskledger.models import utc_now_iso
from taskledger.storage.events import append_event, load_events
from taskledger.storage.indexes import rebuild_v2_indexes
from taskledger.storage.locks import (
    lock_is_expired,
    lock_status,
    read_lock,
    remove_lock,
    write_lock,
)
from taskledger.storage.v2 import (
    ensure_v2_layout,
    list_changes,
    list_introductions,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    overwrite_plan,
    resolve_introduction,
    resolve_plan,
    resolve_question,
    resolve_run,
    resolve_task,
    resolve_v2_paths,
    save_change,
    save_introduction,
    save_plan,
    save_question,
    save_run,
    save_task,
    task_lock_path,
)


def create_task(
    workspace_root: Path,
    *,
    title: str,
    description: str,
    slug: str | None = None,
    priority: str | None = None,
    labels: tuple[str, ...] = (),
    owner: str | None = None,
) -> TaskRecord:
    paths = ensure_v2_layout(workspace_root)
    tasks = list_tasks(workspace_root)
    task_slug = _unique_slug(tasks, slug or title)
    task = TaskRecord(
        id=next_project_id("task", [item.id for item in tasks]),
        slug=task_slug,
        title=title,
        body=description.strip(),
        description_summary=_summary_line(description),
        priority=priority,
        labels=tuple(dict.fromkeys(labels)),
        owner=owner,
    )
    save_task(workspace_root, task)
    _append_event(
        paths.project_dir,
        task.id,
        "task.created",
        {"slug": task.slug, "title": task.title},
    )
    rebuild_v2_indexes(paths)
    return task


def list_task_summaries(workspace_root: Path) -> list[dict[str, object]]:
    tasks = list_tasks(workspace_root)
    return [
        {
            "id": task.id,
            "slug": task.slug,
            "title": task.title,
            "status_stage": task.status_stage,
            "accepted_plan_version": task.accepted_plan_version,
        }
        for task in tasks
    ]


def show_task(workspace_root: Path, ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, ref)
    lock = read_lock(task_lock_path(resolve_v2_paths(workspace_root), task.id))
    plans = list_plans(workspace_root, task.id)
    questions = list_questions(workspace_root, task.id)
    runs = list_runs(workspace_root, task.id)
    changes = list_changes(workspace_root, task.id)
    return {
        "kind": "task",
        "task": task.to_dict(),
        "lock": lock.to_dict() if lock is not None else None,
        "plans": [plan.to_dict() for plan in plans],
        "questions": [question.to_dict() for question in questions],
        "runs": [run.to_dict() for run in runs],
        "changes": [change.to_dict() for change in changes],
    }


def edit_task(
    workspace_root: Path,
    ref: str,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    owner: str | None = None,
    add_labels: tuple[str, ...] = (),
    remove_labels: tuple[str, ...] = (),
    add_notes: tuple[str, ...] = (),
) -> TaskRecord:
    task = resolve_task(workspace_root, ref)
    _enforce_decision(
        metadata_edit_decision(task, _current_lock(workspace_root, task.id))
    )
    labels = [item for item in task.labels if item not in set(remove_labels)]
    for label in add_labels:
        if label not in labels:
            labels.append(label)
    notes = tuple([*task.notes, *[note for note in add_notes if note]])
    updated = replace(
        task,
        title=title or task.title,
        body=description.strip() if description is not None else task.body,
        description_summary=(
            _summary_line(description)
            if description is not None
            else task.description_summary
        ),
        priority=priority or task.priority,
        owner=owner or task.owner,
        labels=tuple(labels),
        notes=notes,
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "task.updated",
        {"title": updated.title},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def cancel_task(
    workspace_root: Path,
    ref: str,
    *,
    reason: str | None = None,
) -> dict[str, object]:
    task = resolve_task(workspace_root, ref)
    require_transition(task.status_stage, "cancelled")
    lock_path = task_lock_path(resolve_v2_paths(workspace_root), task.id)
    lock = read_lock(lock_path)
    if lock is not None:
        _release_lock(
            workspace_root,
            task=task,
            expected_stage=lock.stage,
            run_id=lock.run_id,
            target_stage="cancelled",
            event_name="stage.failed",
            extra_data={"reason": reason or "cancelled"},
        )
        task = resolve_task(workspace_root, ref)
    updated = replace(task, status_stage="cancelled", updated_at=utc_now_iso())
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "task.cancelled",
        {"reason": reason},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "task cancel",
        updated,
        warnings=[],
        changed=True,
    )


def close_task(workspace_root: Path, ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, ref)
    if task.status_stage != "done":
        raise _cli_error(
            "Only done tasks can be closed via task close.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _lifecycle_payload("task close", task, warnings=[], changed=False)


def create_introduction(
    workspace_root: Path,
    *,
    title: str,
    body: str,
    slug: str | None = None,
    labels: tuple[str, ...] = (),
) -> IntroductionRecord:
    intros = list_introductions(workspace_root)
    intro = IntroductionRecord(
        id=next_project_id("intro", [item.id for item in intros]),
        slug=_unique_slug(intros, slug or title),
        title=title,
        body=body.strip(),
        labels=tuple(dict.fromkeys(labels)),
    )
    save_introduction(workspace_root, intro)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return intro


def link_introduction(
    workspace_root: Path, task_ref: str, introduction_ref: str
) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    intro = resolve_introduction(workspace_root, introduction_ref)
    updated = replace(
        task,
        introduction_ref=intro.id,
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "task.updated",
        {"introduction_ref": intro.id},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def add_requirement(
    workspace_root: Path, task_ref: str, required_task_ref: str
) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    required = resolve_task(workspace_root, required_task_ref)
    requirements = list(task.requirements)
    if required.id not in requirements:
        requirements.append(required.id)
    updated = replace(
        task,
        requirements=tuple(requirements),
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def remove_requirement(
    workspace_root: Path, task_ref: str, required_task_ref: str
) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    required = resolve_task(workspace_root, required_task_ref)
    updated = replace(
        task,
        requirements=tuple(item for item in task.requirements if item != required.id),
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def add_file_link(
    workspace_root: Path,
    task_ref: str,
    *,
    path: str,
    kind: str,
    label: str | None = None,
    required_for_validation: bool = False,
) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    links = list(task.file_links)
    existing = next((item for item in links if item.path == path), None)
    new_link = FileLink(
        path=path,
        kind=normalize_file_link_kind(kind),
        label=label,
        required_for_validation=required_for_validation,
    )
    if existing is not None:
        links = [item for item in links if item.path != path]
    links.append(new_link)
    updated = replace(
        task,
        file_links=tuple(links),
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def remove_file_link(workspace_root: Path, task_ref: str, *, path: str) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    updated = replace(
        task,
        file_links=tuple(item for item in task.file_links if item.path != path),
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def list_file_links(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    return {
        "kind": "task_file_links",
        "task_id": task.id,
        "file_links": [item.to_dict() for item in task.file_links],
    }


def add_todo(
    workspace_root: Path,
    task_ref: str,
    *,
    text: str,
    source: str = "user",
    mandatory: bool = False,
) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    actor_role = require_known_actor_role(source)
    _enforce_decision(
        todo_add_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role=actor_role,
        )
    )
    todo = TaskTodo(
        id=next_project_id("todo", [item.id for item in task.todos]),
        text=text.strip(),
        source=source,
        mandatory=mandatory,
    )
    updated = replace(
        task,
        todos=tuple([*task.todos, todo]),
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "todo.added",
        {"todo_id": todo.id, "text": todo.text},
    )
    return updated


def set_todo_done(
    workspace_root: Path, task_ref: str, todo_id: str, *, done: bool
) -> TaskRecord:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        todo_toggle_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role="user",
        )
    )
    now = utc_now_iso()
    todos = [
        replace(todo, done=done, updated_at=now) if todo.id == todo_id else todo
        for todo in task.todos
    ]
    if not any(todo.id == todo_id for todo in task.todos):
        raise _cli_error(f"Todo not found: {todo_id}", EXIT_CODE_MISSING)
    updated = replace(task, todos=tuple(todos), updated_at=now)
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "todo.toggled",
        {"todo_id": todo_id, "done": done},
    )
    return updated


def show_todo(workspace_root: Path, task_ref: str, todo_id: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    for todo in task.todos:
        if todo.id == todo_id:
            return {"kind": "task_todo", "task_id": task.id, "todo": todo.to_dict()}
    raise _cli_error(f"Todo not found: {todo_id}", EXIT_CODE_MISSING)


def start_planning(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    if task.status_stage not in {"draft", "plan_review"}:
        raise _cli_error(
            "Planning can only start from draft or plan_review.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    run = _start_run(workspace_root, task, run_type="planning", stage="planning")
    updated = replace(
        resolve_task(workspace_root, task.id),
        latest_planning_run=run.run_id,
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "plan.started",
        {"run_id": run.run_id},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "plan start",
        updated,
        warnings=[],
        changed=True,
        run=run,
        lock=_require_lock(workspace_root, updated.id),
    )


def propose_plan(
    workspace_root: Path,
    task_ref: str,
    *,
    body: str,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    run = _require_run(workspace_root, task, task.latest_planning_run)
    lock = _lock_for_mutation(workspace_root, task.id)
    _enforce_decision(plan_propose_decision(task, lock, run=run))
    plans = list_plans(workspace_root, task.id)
    version = plans[-1].plan_version + 1 if plans else 1
    plan = PlanRecord(
        task_id=task.id,
        plan_version=version,
        body=body.strip(),
        status="proposed",
        created_by=_default_actor(),
        supersedes=plans[-1].plan_version if plans else None,
        question_refs=tuple(
            item.id
            for item in list_questions(workspace_root, task.id)
            if item.status == "open"
        ),
    )
    save_plan(workspace_root, plan)
    finished_run = replace(
        run,
        status="finished",
        finished_at=utc_now_iso(),
        summary=_summary_line(body),
    )
    save_run(workspace_root, finished_run)
    updated = replace(
        task,
        latest_plan_version=version,
        status_stage="plan_review",
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _release_lock(
        workspace_root,
        task=updated,
        expected_stage="planning",
        run_id=run.run_id,
        target_stage="plan_review",
        event_name="stage.completed",
        extra_data={"plan_version": version},
        delete_only=True,
    )
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "plan.proposed",
        {"plan_version": version},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "plan propose",
        updated,
        warnings=[],
        changed=True,
        plan_version=version,
    )


def show_plan(
    workspace_root: Path, task_ref: str, *, version: int | None = None
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    plan = resolve_plan(
        workspace_root,
        task.id,
        version=version,
    )
    return {
        "kind": "plan",
        "task_id": task.id,
        "plan": plan.to_dict(),
    }


def list_plan_versions(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    plans = list_plans(workspace_root, task.id)
    return {
        "kind": "plan_list",
        "task_id": task.id,
        "plans": [plan.to_dict() for plan in plans],
    }


def diff_plan(
    workspace_root: Path, task_ref: str, *, from_version: int, to_version: int
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    earlier = resolve_plan(workspace_root, task.id, version=from_version)
    later = resolve_plan(workspace_root, task.id, version=to_version)
    diff = "\n".join(
        difflib.unified_diff(
            earlier.body.splitlines(),
            later.body.splitlines(),
            fromfile=f"plan-v{from_version}",
            tofile=f"plan-v{to_version}",
            lineterm="",
        )
    )
    return {
        "kind": "plan_diff",
        "task_id": task.id,
        "from_version": from_version,
        "to_version": to_version,
        "diff": diff,
    }


def approve_plan(
    workspace_root: Path, task_ref: str, *, version: int
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        plan_approve_decision(task, _current_lock(workspace_root, task.id))
    )
    target = resolve_plan(workspace_root, task.id, version=version)
    if target.status == "rejected":
        raise _cli_error(
            f"Rejected plan v{target.plan_version} cannot be approved.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    for plan in list_plans(workspace_root, task.id):
        if plan.plan_version == target.plan_version:
            new_status = "accepted"
        elif plan.status == "rejected":
            new_status = plan.status
        else:
            new_status = "superseded"
        overwrite_plan(workspace_root, replace(plan, status=new_status))
    updated = replace(
        task,
        accepted_plan_version=target.plan_version,
        status_stage="approved",
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "plan.approved",
        {"plan_version": target.plan_version},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "plan approve",
        updated,
        warnings=[],
        changed=True,
        plan_version=target.plan_version,
    )


def reject_plan(
    workspace_root: Path,
    task_ref: str,
    *,
    reason: str | None = None,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        plan_approve_decision(task, _current_lock(workspace_root, task.id))
    )
    latest = resolve_plan(workspace_root, task.id)
    overwrite_plan(workspace_root, replace(latest, status="rejected"))
    updated = replace(task, status_stage="plan_review", updated_at=utc_now_iso())
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "plan.rejected",
        {"plan_version": latest.plan_version, "reason": reason},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "plan reject",
        updated,
        warnings=[],
        changed=True,
        plan_version=latest.plan_version,
    )


def revise_plan(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        plan_revise_decision(task, _current_lock(workspace_root, task.id))
    )
    return start_planning(workspace_root, task_ref)


def add_question(
    workspace_root: Path,
    task_ref: str,
    *,
    text: str,
) -> QuestionRecord:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        question_add_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role="planner",
        )
    )
    question = QuestionRecord(
        id=next_project_id(
            "q",
            [item.id for item in list_questions(workspace_root, task.id)],
        ),
        task_id=task.id,
        question=text.strip(),
        plan_version=task.latest_plan_version,
    )
    save_question(workspace_root, question)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "question.added",
        {"question_id": question.id},
    )
    return question


def answer_question(
    workspace_root: Path,
    task_ref: str,
    question_id: str,
    *,
    text: str,
) -> QuestionRecord:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        question_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role="user",
        )
    )
    question = resolve_question(workspace_root, task.id, question_id)
    answered = replace(
        question,
        status="answered",
        answer=text.strip(),
        answered_at=utc_now_iso(),
        answered_by="user",
    )
    save_question(workspace_root, answered)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "question.answered",
        {"question_id": answered.id},
    )
    return answered


def dismiss_question(
    workspace_root: Path,
    task_ref: str,
    question_id: str,
) -> QuestionRecord:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        question_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role="user",
        )
    )
    question = resolve_question(workspace_root, task.id, question_id)
    dismissed = replace(question, status="dismissed")
    save_question(workspace_root, dismissed)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "question.dismissed",
        {"question_id": dismissed.id},
    )
    return dismissed


def list_open_questions(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    questions = [
        item.to_dict()
        for item in list_questions(workspace_root, task.id)
        if item.status == "open"
    ]
    return {"kind": "task_questions", "task_id": task.id, "questions": questions}


def start_implementation(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    if task.status_stage not in IMPLEMENTABLE_TASK_STAGES:
        raise _cli_error(
            "Implementation requires approved or failed_validation state.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if task.accepted_plan_version is None:
        raise _cli_error(
            "Implementation requires an accepted plan version.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    _ensure_dependencies_done(workspace_root, task)
    run = _start_run(
        workspace_root,
        task,
        run_type="implementation",
        stage="implementing",
    )
    updated = replace(
        resolve_task(workspace_root, task.id),
        latest_implementation_run=run.run_id,
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "implementation.started",
        {"run_id": run.run_id},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "implement start",
        updated,
        warnings=[],
        changed=True,
        run=run,
        lock=_require_lock(workspace_root, updated.id),
    )


def log_implementation(
    workspace_root: Path,
    task_ref: str,
    *,
    message: str,
) -> TaskRunRecord:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_implementation_run,
        expected_type="implementation",
    )
    _enforce_decision(
        implementation_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            run=run,
            action="log implementation work",
        )
    )
    updated = replace(run, worklog=tuple([*run.worklog, message.strip()]))
    save_run(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "implementation.logged",
        {"run_id": run.run_id, "message": message.strip()},
    )
    return updated


def add_implementation_deviation(
    workspace_root: Path,
    task_ref: str,
    *,
    message: str,
) -> TaskRunRecord:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_implementation_run,
        expected_type="implementation",
    )
    _enforce_decision(
        implementation_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            run=run,
            action="record implementation deviations",
        )
    )
    updated = replace(
        run,
        deviations_from_plan=tuple([*run.deviations_from_plan, message.strip()]),
    )
    save_run(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "implementation.logged",
        {"run_id": run.run_id, "deviation": message.strip()},
    )
    return updated


def add_implementation_artifact(
    workspace_root: Path,
    task_ref: str,
    *,
    path: str,
    summary: str,
) -> TaskRunRecord:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_implementation_run,
        expected_type="implementation",
    )
    _enforce_decision(
        implementation_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            run=run,
            action="record implementation artifacts",
        )
    )
    updated = replace(
        run,
        artifact_refs=tuple([*run.artifact_refs, f"{path}: {summary.strip()}"]),
    )
    save_run(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "implementation.logged",
        {"run_id": run.run_id, "artifact": path, "summary": summary.strip()},
    )
    return updated


def add_change(
    workspace_root: Path,
    task_ref: str,
    *,
    path: str,
    kind: str,
    summary: str,
    git_commit: str | None = None,
    git_diff_stat: str | None = None,
    command: str | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
    exit_code: int | None = None,
) -> CodeChangeRecord:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_implementation_run,
        expected_type="implementation",
    )
    _enforce_decision(
        implementation_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            run=run,
            action="record code changes",
        )
    )
    change = CodeChangeRecord(
        change_id=next_project_id(
            "change",
            [item.change_id for item in list_changes(workspace_root, task.id)],
        ),
        task_id=task.id,
        implementation_run=run.run_id,
        timestamp=utc_now_iso(),
        kind=kind,
        path=path,
        summary=summary.strip(),
        git_commit=git_commit,
        git_diff_stat=git_diff_stat,
        command=command,
        before_hash=before_hash,
        after_hash=after_hash,
        exit_code=exit_code,
    )
    save_change(workspace_root, change)
    save_run(
        workspace_root,
        replace(run, change_refs=tuple([*run.change_refs, change.change_id])),
    )
    save_task(
        workspace_root,
        replace(
            task,
            code_change_log_refs=tuple([*task.code_change_log_refs, change.change_id]),
            updated_at=utc_now_iso(),
        ),
    )
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "change.logged",
        {"change_id": change.change_id, "path": path},
    )
    return change


def finish_implementation(
    workspace_root: Path,
    task_ref: str,
    *,
    summary: str,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_implementation_run,
        expected_type="implementation",
    )
    finished = replace(
        run,
        status="finished",
        finished_at=utc_now_iso(),
        summary=summary.strip(),
    )
    save_run(workspace_root, finished)
    updated = replace(task, status_stage="implemented", updated_at=utc_now_iso())
    save_task(workspace_root, updated)
    _release_lock(
        workspace_root,
        task=updated,
        expected_stage="implementing",
        run_id=run.run_id,
        target_stage="implemented",
        event_name="stage.completed",
    )
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "implementation.finished",
        {"run_id": run.run_id},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "implement finish",
        updated,
        warnings=[],
        changed=True,
        run=finished,
    )


def start_validation(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    if task.status_stage != "implemented":
        raise _cli_error(
            "Validation requires implemented state.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    impl_run = _require_run(workspace_root, task, task.latest_implementation_run)
    if impl_run.run_type != "implementation" or impl_run.status != "finished":
        raise _cli_error(
            "Validation requires a finished implementation run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    run = _start_run(
        workspace_root,
        task,
        run_type="validation",
        stage="validating",
    )
    updated_run = replace(run, based_on_implementation_run=impl_run.run_id)
    save_run(workspace_root, updated_run)
    updated = replace(
        resolve_task(workspace_root, task.id),
        latest_validation_run=updated_run.run_id,
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "validation.started",
        {"run_id": updated_run.run_id},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "validate start",
        updated,
        warnings=[],
        changed=True,
        run=updated_run,
        lock=_require_lock(workspace_root, updated.id),
    )


def add_validation_check(
    workspace_root: Path,
    task_ref: str,
    *,
    name: str,
    status: str,
    details: str | None = None,
    evidence: tuple[str, ...] = (),
) -> TaskRunRecord:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_validation_run,
        expected_type="validation",
    )
    _enforce_decision(
        validation_check_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            run=run,
        )
    )
    check = ValidationCheck(
        name=name.strip(),
        status=normalize_validation_check_status(status),
        details=details.strip() if details else None,
        evidence=tuple(item.strip() for item in evidence if item.strip()),
    )
    updated = replace(run, checks=tuple([*run.checks, check]))
    save_run(workspace_root, updated)
    return updated


def finish_validation(
    workspace_root: Path,
    task_ref: str,
    *,
    result: str,
    summary: str,
    recommendation: str | None = None,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_validation_run,
        expected_type="validation",
    )
    normalized_result = normalize_validation_result(result)
    target_stage: TaskStatusStage = (
        "done" if normalized_result == "passed" else "failed_validation"
    )
    finished = replace(
        run,
        status=normalized_result,
        finished_at=utc_now_iso(),
        summary=summary.strip(),
        recommendation=recommendation,
        result=normalized_result,
    )
    save_run(workspace_root, finished)
    updated = replace(task, status_stage=target_stage, updated_at=utc_now_iso())
    save_task(workspace_root, updated)
    _release_lock(
        workspace_root,
        task=updated,
        expected_stage="validating",
        run_id=run.run_id,
        target_stage=target_stage,
        event_name="stage.completed"
        if normalized_result == "passed"
        else "stage.failed",
        extra_data={"result": normalized_result},
    )
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "validation.finished",
        {"run_id": run.run_id, "result": normalized_result},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "validate finish",
        updated,
        warnings=[],
        changed=True,
        run=finished,
        result=normalized_result,
    )


def show_task_run(
    workspace_root: Path,
    task_ref: str,
    *,
    run_id: str | None = None,
    run_type: str,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    selected_run_id = run_id
    if selected_run_id is None:
        if run_type == "implementation":
            selected_run_id = task.latest_implementation_run
        elif run_type == "validation":
            selected_run_id = task.latest_validation_run
        else:
            selected_run_id = task.latest_planning_run
    run = _require_run(workspace_root, task, selected_run_id)
    if run.run_type != run_type:
        raise _cli_error(
            f"Run {run.run_id} is {run.run_type}, not {run_type}.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return {"kind": "task_run", "task_id": task.id, "run": run.to_dict()}


def show_lock(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    lock = _current_lock(workspace_root, task.id)
    return {
        "kind": "task_lock",
        "task_id": task.id,
        "lock": lock.to_dict() if lock is not None else None,
        "status": lock_status(lock),
    }


def break_lock(
    workspace_root: Path,
    task_ref: str,
    *,
    reason: str,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    paths = resolve_v2_paths(workspace_root)
    lock_path = task_lock_path(paths, task.id)
    lock = read_lock(lock_path)
    if lock is None:
        raise _cli_error("No active lock exists for the task.", EXIT_CODE_MISSING)
    _append_event(
        paths.project_dir,
        task.id,
        "lock.broken",
        {"lock_id": lock.lock_id, "reason": reason},
    )
    remove_lock(lock_path)
    rebuild_v2_indexes(paths)
    return {
        "ok": True,
        "command": "lock break",
        "task_id": task.id,
        "status_stage": task.status_stage,
        "changed": True,
        "warnings": [],
        "lock": lock.to_dict(),
        "reason": reason,
    }


def list_locks(workspace_root: Path) -> dict[str, object]:
    locks = load_active_locks(workspace_root)
    return {
        "kind": "task_lock_list",
        "locks": [
            {
                **lock.to_dict(),
                "status": lock_status(lock),
            }
            for lock in locks
        ],
    }


def next_action(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    lock = _current_lock(workspace_root, task.id)
    action: str
    reason: str
    blockers: list[dict[str, str]] = []
    if task.status_stage == "draft":
        action, reason = "plan", "Draft tasks need planning before work starts."
    elif task.status_stage == "planning":
        action, reason = "plan-propose", "Planning is active; propose the next plan."
        if lock is None:
            blockers.append(
                {
                    "kind": "lock",
                    "message": "Planning is active without a planning lock.",
                }
            )
    elif task.status_stage == "plan_review":
        action, reason = "plan-approve", "A proposed plan is waiting for review."
    elif task.status_stage == "approved":
        action, reason = "implement", "The approved plan is ready for implementation."
        if task.accepted_plan_version is None:
            blockers.append(
                {"kind": "approval", "message": "No accepted plan version is recorded."}
            )
        blockers.extend(_dependency_blockers(workspace_root, task))
    elif task.status_stage == "implementing":
        action, reason = "implement-finish", "Implementation is in progress."
        if lock is None:
            blockers.append(
                {
                    "kind": "lock",
                    "message": (
                        "Implementation is active without an "
                        "implementation lock."
                    ),
                }
            )
    elif task.status_stage == "implemented":
        action, reason = "validate", "Implementation is complete and ready to validate."
        impl_run = _optional_run(workspace_root, task, task.latest_implementation_run)
        if (
            impl_run is None
            or impl_run.run_type != "implementation"
            or impl_run.status != "finished"
        ):
            blockers.append(
                {
                    "kind": "implementation",
                    "message": "Validation requires a finished implementation run.",
                }
            )
    elif task.status_stage == "validating":
        action, reason = "validate-finish", "Validation is in progress."
        if lock is None:
            blockers.append(
                {
                    "kind": "lock",
                    "message": "Validation is active without a validation lock.",
                }
            )
    elif task.status_stage == "failed_validation":
        action, reason = "implement", "Validation failed; return to implementation."
        blockers.extend(_dependency_blockers(workspace_root, task))
    elif task.status_stage == "done":
        action, reason = "none", "The task is complete."
    else:
        action, reason = "none", "The task is cancelled."
    return {
        "kind": "task_next_action",
        "task_id": task.id,
        "status_stage": task.status_stage,
        "action": action,
        "reason": reason,
        "blocking": blockers,
    }


def can_perform(workspace_root: Path, task_ref: str, action: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    lock = _current_lock(workspace_root, task.id)
    ok = False
    reason = ""
    blocking: list[dict[str, str]] = []
    if action == "plan":
        ok = task.status_stage in {"draft", "plan_review"} and lock is None
        reason = (
            "Planning can start from draft or after plan review."
            if ok
            else (
                "Planning is only available from draft or plan_review "
                "without an active lock."
            )
        )
        if lock is not None:
            blocking.append(
                {
                    "kind": "lock",
                    "message": (
                        f"Task has an active {lock.stage} lock "
                        f"from {lock.run_id}."
                    ),
                }
            )
    elif action == "implement":
        ok = (
            task.status_stage in IMPLEMENTABLE_TASK_STAGES
            and task.accepted_plan_version is not None
            and not _dependency_blockers(workspace_root, task)
            and lock is None
        )
        reason = (
            "Implementation is ready."
            if ok
            else (
                "Implementation requires an accepted plan, valid stage, "
                "no conflicting lock, and completed dependencies."
            )
        )
        if task.accepted_plan_version is None:
            blocking.append(
                {"kind": "approval", "message": "No accepted plan version."}
            )
        blocking.extend(_dependency_blockers(workspace_root, task))
        if lock is not None:
            blocking.append(
                {
                    "kind": "lock",
                    "message": (
                        f"Task has an active {lock.stage} lock "
                        f"from {lock.run_id}."
                    ),
                }
            )
    elif action == "validate":
        impl_run = _optional_run(workspace_root, task, task.latest_implementation_run)
        ok = (
            task.status_stage == "implemented"
            and lock is None
            and impl_run is not None
            and impl_run.run_type == "implementation"
            and impl_run.status == "finished"
        )
        reason = (
            "Validation is ready."
            if ok
            else (
                "Validation requires implemented state, a finished "
                "implementation run, and no conflicting lock."
            )
        )
        if (
            impl_run is None
            or impl_run.run_type != "implementation"
            or impl_run.status != "finished"
        ):
            blocking.append(
                {
                    "kind": "implementation",
                    "message": "No finished implementation run is available.",
                }
            )
        if lock is not None:
            blocking.append(
                {
                    "kind": "lock",
                    "message": (
                        f"Task has an active {lock.stage} lock "
                        f"from {lock.run_id}."
                    ),
                }
            )
    else:
        raise _cli_error(f"Unsupported action: {action}", EXIT_CODE_BAD_INPUT)
    return {
        "kind": "task_capability",
        "task_id": task.id,
        "action": action,
        "ok": ok,
        "reason": reason,
        "blocking": blocking,
    }


def reindex(workspace_root: Path) -> dict[str, object]:
    paths = ensure_v2_layout(workspace_root)
    counts = rebuild_v2_indexes(paths)
    _append_event(paths.project_dir, "*", "doctor.reindexed", counts)
    return {"kind": "taskledger_reindex", "counts": counts}


def list_events(workspace_root: Path) -> list[dict[str, object]]:
    events_dir = resolve_v2_paths(workspace_root).events_dir
    return [item.to_dict() for item in load_events(events_dir)]


def _start_run(
    workspace_root: Path,
    task: TaskRecord,
    *,
    run_type: str,
    stage: str,
) -> TaskRunRecord:
    run_prefix = {
        "planning": "plan-run",
        "implementation": "impl-run",
        "validation": "val-run",
    }[run_type]
    run = TaskRunRecord(
        run_id=next_project_id(
            run_prefix,
            [item.run_id for item in list_runs(workspace_root, task.id)],
        ),
        task_id=task.id,
        run_type=run_type,  # type: ignore[arg-type]
        actor=_default_actor(),
        based_on_plan_version=task.accepted_plan_version or task.latest_plan_version,
    )
    save_run(workspace_root, run)
    _acquire_lock(
        workspace_root,
        task=task,
        stage=stage,
        run=run,
        reason={
            "planning": "plan task",
            "implementation": "implement approved plan",
            "validation": "validate implementation",
        }[run_type],
    )
    return run


def _acquire_lock(
    workspace_root: Path,
    *,
    task: TaskRecord,
    stage: str,
    run: TaskRunRecord,
    reason: str,
) -> TaskLock:
    if stage not in ACTIVE_TASK_STAGES:
        raise _cli_error("Only active stages can acquire locks.", EXIT_CODE_BAD_INPUT)
    if stage == "planning":
        require_transition(task.status_stage, "planning")
    elif stage == "implementing":
        require_transition(task.status_stage, "implementing")
    elif stage == "validating":
        require_transition(task.status_stage, "validating")
    paths = resolve_v2_paths(workspace_root)
    lock_path = task_lock_path(paths, task.id)
    existing = read_lock(lock_path)
    if existing is not None:
        if existing.run_id == run.run_id:
            return existing
        raise _cli_error(
            _lock_conflict_message(task.id, existing), EXIT_CODE_LOCK_CONFLICT
        )
    now = datetime.now(timezone.utc)
    lock = TaskLock(
        lock_id=next_project_id(
            "lock",
            [item.lock_id for item in load_active_locks(workspace_root)],
        ),
        task_id=task.id,
        stage=stage,
        run_id=run.run_id,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(hours=2)).isoformat(),
        reason=reason,
        holder=_default_actor(),
    )
    try:
        write_lock(lock_path, lock)
    except LaunchError as exc:
        raise _cli_error(
            _lock_conflict_message(task.id, read_lock(lock_path) or lock),
            EXIT_CODE_LOCK_CONFLICT,
        ) from exc
    updated = replace(task, status_stage=stage, updated_at=utc_now_iso())
    save_task(workspace_root, updated)
    _append_event(paths.project_dir, task.id, "lock.acquired", lock.to_dict())
    _append_event(
        paths.project_dir,
        task.id,
        "stage.entered",
        {"stage": stage, "run_id": run.run_id},
    )
    return lock


def _release_lock(
    workspace_root: Path,
    *,
    task: TaskRecord,
    expected_stage: str,
    run_id: str,
    target_stage: TaskStatusStage,
    event_name: str,
    extra_data: dict[str, object] | None = None,
    delete_only: bool = False,
) -> None:
    paths = resolve_v2_paths(workspace_root)
    lock_path = task_lock_path(paths, task.id)
    lock = read_lock(lock_path)
    if lock is None:
        raise _cli_error(
            f"Task {task.id} has no active {expected_stage} lock to release.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    if lock.stage != expected_stage or lock.run_id != run_id:
        raise _cli_error(
            "Active lock does not match the expected stage/run.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    data = {"stage": expected_stage, "run_id": run_id, **(extra_data or {})}
    _append_event(paths.project_dir, task.id, event_name, data)
    remove_lock(lock_path)
    _append_event(
        paths.project_dir,
        task.id,
        "lock.released",
        {"lock_id": lock.lock_id, "stage": expected_stage},
    )
    if delete_only:
        return
    save_task(
        workspace_root,
        replace(task, status_stage=target_stage, updated_at=utc_now_iso()),
    )


def _ensure_dependencies_done(workspace_root: Path, task: TaskRecord) -> None:
    blocked = []
    for requirement in task.requirements:
        required = resolve_task(workspace_root, requirement)
        if required.status_stage != "done":
            blocked.append(required.id)
    if blocked:
        raise _cli_error(
            "Implementation is blocked by incomplete requirements: "
            + ", ".join(blocked),
            EXIT_CODE_DEPENDENCY_BLOCKED,
        )


def _require_lock(workspace_root: Path, task_id: str) -> TaskLock:
    lock = _current_lock(workspace_root, task_id)
    if lock is None:
        raise _cli_error("No active lock found.", EXIT_CODE_LOCK_CONFLICT)
    if lock_is_expired(lock):
        raise _cli_error(_lock_conflict_message(task_id, lock), EXIT_CODE_LOCK_CONFLICT)
    return lock


def _require_run(
    workspace_root: Path,
    task: TaskRecord,
    run_id: str | None,
) -> TaskRunRecord:
    if run_id is None:
        raise _cli_error("No active run is recorded for the task.", EXIT_CODE_MISSING)
    return resolve_run(workspace_root, task.id, run_id)


def _optional_run(
    workspace_root: Path,
    task: TaskRecord,
    run_id: str | None,
) -> TaskRunRecord | None:
    if run_id is None:
        return None
    try:
        return resolve_run(workspace_root, task.id, run_id)
    except LaunchError:
        return None


def _require_running_run(
    workspace_root: Path,
    task: TaskRecord,
    run_id: str | None,
    *,
    expected_type: str,
) -> TaskRunRecord:
    run = _require_run(workspace_root, task, run_id)
    if run.run_type != expected_type or run.status != "running":
        raise _cli_error(
            f"Task does not have a running {expected_type} run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return run


def _current_lock(workspace_root: Path, task_id: str) -> TaskLock | None:
    return read_lock(task_lock_path(resolve_v2_paths(workspace_root), task_id))


def _lock_for_mutation(workspace_root: Path, task_id: str) -> TaskLock | None:
    lock = _current_lock(workspace_root, task_id)
    if lock is not None and lock_is_expired(lock):
        raise _cli_error(_lock_conflict_message(task_id, lock), EXIT_CODE_LOCK_CONFLICT)
    return lock


def _dependency_blockers(
    workspace_root: Path, task: TaskRecord
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for requirement in task.requirements:
        required = resolve_task(workspace_root, requirement)
        if required.status_stage != "done":
            blockers.append(
                {
                    "kind": "dependency",
                    "message": (
                        f"Requirement {required.id} is still "
                        f"{required.status_stage}."
                    ),
                }
            )
    return blockers


def _lock_conflict_message(task_id: str, lock: TaskLock) -> str:
    if lock_is_expired(lock):
        return (
            f"Task {task_id} has an expired {lock.stage} lock from {lock.run_id}. "
            f'Break it explicitly with: taskledger lock break {task_id} --reason "..."'
        )
    return f"Task {task_id} is locked by {lock.run_id} for {lock.stage}."


def _enforce_decision(decision) -> None:
    if decision.ok:
        return
    raise _cli_error(decision.reason, decision.exit_code)


def _default_actor() -> ActorRef:
    return ActorRef(
        actor_type="agent",
        actor_name=getpass.getuser() or "taskledger",
        host=socket.gethostname(),
        pid=os.getpid(),
    )


def _append_event(
    project_dir: Path,
    task_id: str,
    event_name: str,
    data: dict[str, object],
) -> None:
    append_event(
        project_dir / "events",
        TaskEvent(
            ts=utc_now_iso(),
            event=event_name,
            task_id=task_id,
            actor=_default_actor(),
            data=data,
        ),
    )


def _summary_line(text: str | None) -> str | None:
    if text is None:
        return None
    stripped = " ".join(text.split())
    return stripped[:117] + "..." if len(stripped) > 120 else stripped


def _unique_slug(existing: list, value: str) -> str:
    base = slugify_project_ref(value, empty="task")
    taken = {item.slug for item in existing}
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def _lifecycle_payload(
    command: str,
    task: TaskRecord,
    *,
    warnings: list[str],
    changed: bool,
    plan_version: int | None = None,
    run: TaskRunRecord | None = None,
    lock: TaskLock | None = None,
    result: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": True,
        "command": command,
        "task_id": task.id,
        "status_stage": task.status_stage,
        "changed": changed,
        "warnings": warnings,
        "lock": lock.to_dict() if lock is not None else None,
    }
    if plan_version is not None:
        payload["plan_version"] = plan_version
    if run is not None:
        payload["run_id"] = run.run_id
    if result is not None:
        payload["result"] = result
    return payload


def _cli_error(message: str, exit_code: int) -> LaunchError:
    error = LaunchError(message)
    error.taskledger_exit_code = exit_code
    return error
