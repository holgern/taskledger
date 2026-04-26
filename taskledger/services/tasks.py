from __future__ import annotations

import difflib
import getpass
import hashlib
import os
import shlex
import socket
import subprocess
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

import yaml

from taskledger.domain.models import (
    AcceptanceCriterion,
    ActiveTaskState,
    ActorRef,
    CodeChangeRecord,
    CriterionWaiver,
    DependencyRequirement,
    DependencyWaiver,
    FileLink,
    HarnessRef,
    IntroductionRecord,
    LinkCollection,
    PlanRecord,
    QuestionRecord,
    RequirementCollection,
    TaskEvent,
    TaskLock,
    TaskRecord,
    TaskRunRecord,
    TaskTodo,
    TodoCollection,
    ValidationCheck,
)
from taskledger.domain.policies import (
    Decision,
    derive_active_stage,
    implementation_mutation_decision,
    metadata_edit_decision,
    plan_approve_decision,
    plan_command_decision,
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
    EXIT_CODE_GENERIC_FAILURE,
    EXIT_CODE_INVALID_TRANSITION,
    EXIT_CODE_LOCK_CONFLICT,
    EXIT_CODE_MISSING,
    EXIT_CODE_STALE_LOCK_REQUIRES_BREAK,
    EXIT_CODE_VALIDATION_FAILED,
    IMPLEMENTABLE_TASK_STAGES,
    TaskStatusStage,
    normalize_file_link_kind,
    normalize_run_type,
    normalize_validation_check_status,
    normalize_validation_result,
    require_transition,
)
from taskledger.errors import LaunchError, LockConflict, NoActiveTask
from taskledger.ids import next_project_id, slugify_project_ref
from taskledger.storage.atomic import atomic_write_text
from taskledger.storage.events import append_event, load_events, next_event_id
from taskledger.storage.indexes import rebuild_v2_indexes
from taskledger.storage.locks import (
    lock_is_expired,
    lock_status,
    read_lock,
    remove_lock,
    write_lock,
)
from taskledger.storage.v2 import (
    V2Paths,
    ensure_v2_layout,
    list_changes,
    list_introductions,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    load_active_task_state,
    load_links,
    load_requirements,
    load_todos,
    overwrite_plan,
    resolve_introduction,
    resolve_plan,
    resolve_question,
    resolve_run,
    resolve_task,
    resolve_v2_paths,
    save_active_task_state,
    save_change,
    save_introduction,
    save_links,
    save_plan,
    save_question,
    save_requirements,
    save_run,
    save_task,
    save_todos,
    task_artifacts_dir,
    task_audit_dir,
    task_lock_path,
)
from taskledger.storage.v2 import (
    resolve_active_task as storage_resolve_active_task,
)
from taskledger.timeutils import utc_now_iso


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
    active_state = load_active_task_state(workspace_root)
    active_task_id = active_state.task_id if active_state is not None else None
    return [
        {
            "id": task.id,
            "slug": task.slug,
            "title": task.title,
            "status": task.status_stage,
            "status_stage": task.status_stage,
            "is_active": task.id == active_task_id,
            "active_stage": _task_active_stage(workspace_root, task),
            "accepted_plan_version": task.accepted_plan_version,
        }
        for task in tasks
    ]


def resolve_active_task(workspace_root: Path) -> TaskRecord:
    return storage_resolve_active_task(workspace_root)


def show_active_task(workspace_root: Path) -> dict[str, object]:
    state = load_active_task_state(workspace_root)
    if state is None:
        raise NoActiveTask()
    task = storage_resolve_active_task(workspace_root)
    return _active_task_payload(
        workspace_root,
        task,
        state=state,
        changed=False,
        previous_task_id=state.previous_task_id,
    )


def activate_task(
    workspace_root: Path,
    ref: str,
    *,
    reason: str | None = None,
    actor_type: str = "user",
    force: bool = False,
) -> dict[str, object]:
    task = resolve_task(workspace_root, ref)
    previous = load_active_task_state(workspace_root)
    previous_task_id = previous.task_id if previous is not None else None
    if previous_task_id == task.id and previous is not None:
        return _active_task_payload(
            workspace_root,
            task,
            state=previous,
            changed=False,
            previous_task_id=previous.previous_task_id,
        )
    if previous_task_id is not None:
        _ensure_active_switch_allowed(
            workspace_root,
            previous_task_id,
            force=force,
            reason=reason,
        )
    state = ActiveTaskState(
        task_id=task.id,
        activated_by=_actor_for_active_task(actor_type),
        reason=reason,
        previous_task_id=previous_task_id,
    )
    save_active_task_state(workspace_root, state)
    project_dir = resolve_v2_paths(workspace_root).project_dir
    if previous_task_id is not None:
        _append_event(
            project_dir,
            previous_task_id,
            "task.deactivated",
            {"reason": reason, "next_task_id": task.id, "forced": force},
        )
    _append_event(
        project_dir,
        task.id,
        "task.activated",
        {"reason": reason, "previous_task_id": previous_task_id, "forced": force},
    )
    return _active_task_payload(
        workspace_root,
        task,
        state=state,
        changed=True,
        previous_task_id=previous_task_id,
    )


def deactivate_task(
    workspace_root: Path,
    *,
    reason: str,
    actor_type: str = "user",
    force: bool = False,
) -> dict[str, object]:
    return clear_active_task(
        workspace_root,
        reason=reason,
        actor_type=actor_type,
        force=force,
    )


def clear_active_task(
    workspace_root: Path,
    *,
    reason: str,
    actor_type: str = "user",
    force: bool = False,
) -> dict[str, object]:
    from taskledger.storage.v2 import clear_active_task_state

    state = load_active_task_state(workspace_root)
    if state is None:
        raise NoActiveTask()
    _ensure_active_switch_allowed(
        workspace_root,
        state.task_id,
        force=force,
        reason=reason,
    )
    task = storage_resolve_active_task(workspace_root)
    clear_active_task_state(workspace_root)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "task.deactivated",
        {"reason": reason, "forced": force, "actor_type": actor_type},
    )
    return _active_task_payload(
        workspace_root,
        task,
        state=state,
        changed=True,
        previous_task_id=state.previous_task_id,
        active=False,
    )


def show_task(workspace_root: Path, ref: str) -> dict[str, object]:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, ref))
    lock = read_lock(task_lock_path(resolve_v2_paths(workspace_root), task.id))
    plans = list_plans(workspace_root, task.id)
    questions = list_questions(workspace_root, task.id)
    runs = list_runs(workspace_root, task.id)
    changes = list_changes(workspace_root, task.id)
    active_stage = _task_active_stage(
        workspace_root,
        task,
        lock=lock,
        runs=runs,
    )
    return {
        "kind": "task",
        "task": _task_payload(task, active_stage=active_stage),
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
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    required = resolve_task(workspace_root, required_task_ref)
    requirements = list(task.requirements)
    if required.id not in requirements:
        requirements.append(required.id)
    updated = replace(
        task,
        requirements=tuple(requirements),
        updated_at=utc_now_iso(),
    )
    save_requirements(
        workspace_root,
        RequirementCollection(
            task_id=updated.id,
            requirements=tuple(
                DependencyRequirement(task_id=item) for item in requirements
            ),
        ),
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def remove_requirement(
    workspace_root: Path, task_ref: str, required_task_ref: str
) -> TaskRecord:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    required = resolve_task(workspace_root, required_task_ref)
    remaining = tuple(item for item in task.requirements if item != required.id)
    updated = replace(
        task,
        requirements=remaining,
        updated_at=utc_now_iso(),
    )
    save_requirements(
        workspace_root,
        RequirementCollection(
            task_id=updated.id,
            requirements=tuple(
                DependencyRequirement(task_id=item) for item in remaining
            ),
        ),
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def waive_requirement(
    workspace_root: Path,
    task_ref: str,
    required_task_ref: str,
    *,
    actor_type: str,
    reason: str,
) -> TaskRecord:
    if actor_type != "user":
        raise _cli_error(
            "Only user dependency waivers can unblock implementation.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    if not reason.strip():
        raise _cli_error("Dependency waiver requires --reason.", EXIT_CODE_BAD_INPUT)
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    required = resolve_task(workspace_root, required_task_ref)
    sidecar = load_requirements(workspace_root, task.id)
    requirements = list(sidecar.requirements)
    for index, item in enumerate(requirements):
        if item.task_id == required.id:
            requirements[index] = replace(
                item,
                waiver=DependencyWaiver(
                    actor=ActorRef(
                        actor_type="user",
                        actor_name=getpass.getuser() or "user",
                        tool="manual",
                    ),
                    reason=reason.strip(),
                ),
            )
            break
    else:
        requirements.append(
            DependencyRequirement(
                task_id=required.id,
                waiver=DependencyWaiver(
                    actor=ActorRef(
                        actor_type="user",
                        actor_name=getpass.getuser() or "user",
                        tool="manual",
                    ),
                    reason=reason.strip(),
                ),
            )
        )
    save_requirements(
        workspace_root,
        RequirementCollection(task_id=task.id, requirements=tuple(requirements)),
    )
    updated = replace(
        task,
        requirements=tuple(item.task_id for item in requirements),
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "requirement.waived",
        {"required_task_id": required.id, "reason": reason.strip()},
    )
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
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
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
    save_links(
        workspace_root, LinkCollection(task_id=updated.id, links=updated.file_links)
    )
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def remove_file_link(workspace_root: Path, task_ref: str, *, path: str) -> TaskRecord:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    remaining = tuple(item for item in task.file_links if item.path != path)
    updated = replace(
        task,
        file_links=remaining,
        updated_at=utc_now_iso(),
    )
    save_links(workspace_root, LinkCollection(task_id=updated.id, links=remaining))
    save_task(workspace_root, updated)
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return updated


def list_file_links(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
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
    source: str | None = None,
    mandatory: bool = False,
) -> TaskRecord:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    lock = _lock_for_mutation(workspace_root, task.id)
    # Infer source from active lock unless explicitly provided
    if source is not None:
        resolved_source = source
    elif lock is not None and lock.stage == "planning":
        resolved_source = "planner"
    elif lock is not None and lock.stage == "implementing":
        resolved_source = "implementer"
    else:
        resolved_source = "user"
    actor_role = require_known_actor_role(resolved_source)
    _enforce_decision(
        todo_add_decision(
            task,
            lock,
            actor_role=actor_role,
        )
    )
    todo = TaskTodo(
        id=next_project_id("todo", [item.id for item in task.todos]),
        text=text.strip(),
        source=resolved_source,
        mandatory=mandatory,
        active_at=utc_now_iso()
        if lock is not None and lock.stage == "implementing"
        else None,
    )
    updated = replace(
        task,
        todos=tuple([*task.todos, todo]),
        updated_at=utc_now_iso(),
    )
    save_todos(workspace_root, TodoCollection(task_id=updated.id, todos=updated.todos))
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "todo.added",
        {"todo_id": todo.id, "text": todo.text},
    )
    return updated


def set_todo_done(
    workspace_root: Path,
    task_ref: str,
    todo_id: str,
    *,
    done: bool,
    evidence: str | None = None,
    artifacts: tuple[str, ...] = (),
    changes: tuple[str, ...] = (),
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> TaskRecord:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    normalized_todo_id = _normalize_local_id(todo_id, "todo")
    _enforce_decision(
        todo_toggle_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role="user",
        )
    )
    now = utc_now_iso()
    resolved_actor = actor or _default_actor()
    todos = [
        replace(
            todo,
            done=done,
            status="done" if done else "open",
            updated_at=now,
            done_at=now if done else None,
            completed_by=resolved_actor if done else None,
            completed_in_harness=harness if done else None,
            evidence=(
                tuple([*todo.evidence, evidence.strip()])
                if done and evidence and evidence.strip()
                else todo.evidence
            ),
            artifact_refs=tuple([*todo.artifact_refs, *artifacts])
            if done
            else todo.artifact_refs,
            change_refs=tuple([*todo.change_refs, *changes])
            if done
            else todo.change_refs,
        )
        if todo.id in {todo_id, normalized_todo_id}
        else todo
        for todo in task.todos
    ]
    if not any(todo.id in {todo_id, normalized_todo_id} for todo in task.todos):
        raise _cli_error(f"Todo not found: {todo_id}", EXIT_CODE_MISSING)
    updated = replace(task, todos=tuple(todos), updated_at=now)
    save_todos(workspace_root, TodoCollection(task_id=updated.id, todos=updated.todos))
    save_task(workspace_root, updated)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "todo.completed" if done else "todo.toggled",
        {
            "todo_id": todo_id,
            "done": done,
            "evidence": evidence,
            "artifacts": list(artifacts),
            "changes": list(changes),
        },
    )
    return updated


def show_todo(workspace_root: Path, task_ref: str, todo_id: str) -> dict[str, object]:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    normalized_todo_id = _normalize_local_id(todo_id, "todo")
    for todo in task.todos:
        if todo.id == todo_id or todo.id == normalized_todo_id:
            return {"kind": "task_todo", "task_id": task.id, "todo": todo.to_dict()}
    raise _cli_error(f"Todo not found: {todo_id}", EXIT_CODE_MISSING)


def start_planning(
    workspace_root: Path,
    task_ref: str,
    *,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    if task.status_stage not in {"draft", "plan_review"}:
        raise _cli_error(
            "Planning can only start from draft or plan_review.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    run = _start_run(
        workspace_root,
        task,
        run_type="planning",
        stage="planning",
        actor=actor,
        harness=harness,
    )
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
    criteria: tuple[str, ...] = (),
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    run = _require_run(workspace_root, task, task.latest_planning_run)
    lock = _lock_for_mutation(workspace_root, task.id)
    _enforce_decision(plan_propose_decision(task, lock, run=run))
    plans = list_plans(workspace_root, task.id)
    version = plans[-1].plan_version + 1 if plans else 1
    front_matter, plan_body = _parse_plan_front_matter(body)
    questions = list_questions(workspace_root, task.id)
    plan = PlanRecord(
        task_id=task.id,
        plan_version=version,
        body=plan_body.strip(),
        status="proposed",
        created_by=_default_actor(),
        supersedes=plans[-1].plan_version if plans else None,
        question_refs=tuple(item.id for item in questions if item.status == "open"),
        criteria=_criteria_from_plan_input(front_matter, criteria),
        todos=_todos_from_plan_input(front_matter),
        generation_reason=_optional_front_matter_string(
            front_matter, "generation_reason"
        )
        or "initial",
        based_on_question_ids=tuple(
            item.id for item in questions if item.status == "answered"
        ),
        based_on_answer_hash=_answer_snapshot_hash(questions),
    )
    save_plan(workspace_root, plan)
    finished_run = replace(
        run,
        status="finished",
        finished_at=utc_now_iso(),
        summary=_summary_line(plan_body),
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


def upsert_plan(
    workspace_root: Path,
    task_ref: str,
    *,
    body: str,
    criteria: tuple[str, ...] = (),
    from_answers: bool = False,
    allow_open_questions: bool = False,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    questions = list_questions(workspace_root, task.id)
    open_required = _required_open_question_ids(questions)
    if open_required and not allow_open_questions:
        raise _cli_error(
            "Plan upsert is blocked by required open questions: "
            + ", ".join(open_required),
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    latest_plan = _latest_plan_or_none(workspace_root, task.id)
    stale_answers = (
        _stale_answer_question_ids(questions, latest_plan)
        if latest_plan is not None
        else [
            item.id
            for item in questions
            if item.status == "answered" and item.required_for_plan
        ]
    )
    if from_answers or stale_answers:
        payload = regenerate_plan_from_answers(
            workspace_root,
            task.id,
            body=body,
            criteria=criteria,
            allow_open_questions=allow_open_questions,
        )
        payload["operation"] = "regenerated"
        payload["command"] = "plan upsert"
        return payload
    payload = propose_plan(workspace_root, task.id, body=body, criteria=criteria)
    payload["operation"] = "proposed"
    payload["command"] = "plan upsert"
    return payload


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
    workspace_root: Path,
    task_ref: str,
    *,
    version: int,
    actor_type: str = "user",
    actor_name: str | None = None,
    note: str | None = None,
    allow_agent_approval: bool = False,
    reason: str | None = None,
    allow_empty_criteria: bool = False,
    materialize_todos: bool = True,
    allow_open_questions: bool = False,
    allow_empty_todos: bool = False,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        plan_approve_decision(task, _current_lock(workspace_root, task.id))
    )
    questions = list_questions(workspace_root, task.id)
    open_questions = _required_open_question_ids(questions)
    if open_questions and not allow_open_questions:
        raise _cli_error(
            "Plan approval is blocked by open planning questions: "
            + ", ".join(open_questions),
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    if allow_open_questions and not (reason or "").strip():
        raise _cli_error(
            "--allow-open-questions requires --reason.", EXIT_CODE_BAD_INPUT
        )
    target = resolve_plan(workspace_root, task.id, version=version)
    if target.status != "proposed":
        raise _cli_error(
            "Only proposed plan versions can be approved. "
            f"v{target.plan_version} is {target.status}.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    stale_answer_ids = _stale_answer_question_ids(questions, target)
    if stale_answer_ids:
        error = _cli_error(
            "Plan approval is blocked by answered planning questions that are not "
            "reflected in this plan. Regenerate the plan from answers first: "
            + ", ".join(stale_answer_ids),
            EXIT_CODE_APPROVAL_REQUIRED,
        )
        error.taskledger_error_code = "APPROVAL_REQUIRED"
        raise error
    if not target.criteria and not allow_empty_criteria:
        raise _cli_error(
            "Plan approval requires at least one acceptance criterion.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    if allow_empty_criteria and not (reason or "").strip():
        raise _cli_error(
            "--allow-empty-criteria requires --reason.", EXIT_CODE_BAD_INPUT
        )
    if not target.todos and not allow_empty_todos:
        raise _cli_error(
            "Plan approval requires at least one todo. "
            'Use --allow-empty-todos --reason "..." for trivial tasks.',
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    if allow_empty_todos and not (reason or "").strip():
        raise _cli_error("--allow-empty-todos requires --reason.", EXIT_CODE_BAD_INPUT)
    if not materialize_todos and not (reason or "").strip():
        raise _cli_error(
            "--no-materialize-todos requires --reason.", EXIT_CODE_BAD_INPUT
        )
    approved_by = _approval_actor(
        actor_type=actor_type,
        actor_name=actor_name,
        note=note,
        allow_agent_approval=allow_agent_approval,
        reason=reason,
    )
    approval_note = (note or reason or "").strip()
    for plan in list_plans(workspace_root, task.id):
        if plan.plan_version == target.plan_version:
            updated_plan = replace(
                plan,
                status="accepted",
                approved_at=utc_now_iso(),
                approved_by=approved_by,
                approval_note=approval_note,
            )
        elif plan.status == "rejected":
            updated_plan = plan
        else:
            updated_plan = replace(plan, status="superseded")
        overwrite_plan(workspace_root, updated_plan)
    updated = replace(
        task,
        accepted_plan_version=target.plan_version,
        status_stage="approved",
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    materialized = 0
    if materialize_todos:
        materialized_result = materialize_plan_todos(
            workspace_root,
            updated.id,
            version=target.plan_version,
        )
        materialized = materialized_result["materialized_todos"]
        updated = resolve_task(workspace_root, updated.id)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "plan.approved",
        {
            "plan_version": target.plan_version,
            "approved_by": approved_by.to_dict(),
            "approval_note": approval_note,
        },
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    payload = _lifecycle_payload(
        "plan approve",
        updated,
        warnings=[],
        changed=True,
        plan_version=target.plan_version,
        result=f"materialized_todos={materialized}",
    )
    payload["materialized_todos"] = materialized
    payload["mandatory_todos"] = len(
        [
            todo
            for todo in load_todos(workspace_root, updated.id).todos
            if todo.mandatory
        ]
    )
    payload["next_action"] = "taskledger implement start"
    return payload


class PlanTodoMaterializationPayload(TypedDict):
    kind: str
    task_id: str
    plan_id: str
    materialized_todos: int
    todos: list[dict[str, object]]
    dry_run: bool


def materialize_plan_todos(
    workspace_root: Path,
    task_ref: str,
    *,
    version: int,
    dry_run: bool = False,
) -> PlanTodoMaterializationPayload:
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    plan = resolve_plan(workspace_root, task.id, version=version)
    existing_keys = {
        (todo.source_plan_id, _normalize_todo_text(todo.text)) for todo in task.todos
    }
    new_todos: list[TaskTodo] = []
    next_ids = [todo.id for todo in task.todos]
    for plan_todo in plan.todos:
        key = (plan.plan_id, _normalize_todo_text(plan_todo.text))
        if key in existing_keys:
            continue
        todo_id = next_project_id("todo", [*next_ids, *(todo.id for todo in new_todos)])
        new_todos.append(
            replace(
                plan_todo,
                id=todo_id,
                source="plan",
                source_plan_id=plan.plan_id,
                mandatory=plan_todo.mandatory,
                status="open",
                done=False,
                created_at=utc_now_iso(),
                updated_at=utc_now_iso(),
            )
        )
    if new_todos and not dry_run:
        updated = replace(
            task,
            todos=tuple([*task.todos, *new_todos]),
            updated_at=utc_now_iso(),
        )
        save_todos(
            workspace_root, TodoCollection(task_id=updated.id, todos=updated.todos)
        )
        save_task(workspace_root, updated)
        _append_event(
            resolve_v2_paths(workspace_root).project_dir,
            updated.id,
            "todo.added",
            {
                "source_plan_id": plan.plan_id,
                "todo_ids": [todo.id for todo in new_todos],
            },
        )
    return PlanTodoMaterializationPayload(
        kind="plan_todo_materialization",
        task_id=task.id,
        plan_id=plan.plan_id,
        materialized_todos=len(new_todos),
        todos=[todo.to_dict() for todo in new_todos],
        dry_run=dry_run,
    )


def regenerate_plan_from_answers(
    workspace_root: Path,
    task_ref: str,
    *,
    body: str,
    criteria: tuple[str, ...] = (),
    allow_open_questions: bool = False,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    questions = list_questions(workspace_root, task.id)
    open_required = [
        item.id
        for item in questions
        if item.status == "open" and item.required_for_plan
    ]
    if open_required and not allow_open_questions:
        raise _cli_error(
            "Plan regeneration is blocked by required open questions: "
            + ", ".join(open_required),
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    answered = [
        item
        for item in questions
        if item.status == "answered" and item.required_for_plan
    ]
    plans = list_plans(workspace_root, task.id)
    if not answered and not plans:
        raise _cli_error(
            "Plan regeneration requires answered questions or a previous plan.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    front_matter, plan_body = _parse_plan_front_matter(body)
    version = plans[-1].plan_version + 1 if plans else 1
    plan = PlanRecord(
        task_id=task.id,
        plan_version=version,
        body=plan_body.strip(),
        status="proposed",
        created_by=_default_actor(),
        supersedes=plans[-1].plan_version if plans else None,
        question_refs=tuple(open_required),
        criteria=_criteria_from_plan_input(front_matter, criteria),
        todos=_todos_from_plan_input(front_matter),
        generation_reason="after_questions",
        based_on_question_ids=tuple(item.id for item in answered),
        based_on_answer_hash=_answer_snapshot_hash(questions),
    )
    save_plan(workspace_root, plan)
    if plans:
        previous = plans[-1]
        if previous.status == "proposed":
            overwrite_plan(workspace_root, replace(previous, status="superseded"))
    run_to_finish: TaskRunRecord | None = None
    lock_to_release = _current_lock(workspace_root, task.id)
    if task.latest_planning_run is not None:
        candidate_run = _optional_run(workspace_root, task, task.latest_planning_run)
        if (
            candidate_run is not None
            and candidate_run.run_type == "planning"
            and candidate_run.status == "running"
            and lock_to_release is not None
            and lock_to_release.stage == "planning"
            and lock_to_release.run_id == candidate_run.run_id
        ):
            run_to_finish = candidate_run
            save_run(
                workspace_root,
                replace(
                    candidate_run,
                    status="finished",
                    finished_at=utc_now_iso(),
                    summary=_summary_line(plan_body),
                ),
            )
    updated = replace(
        task,
        latest_plan_version=version,
        status_stage="plan_review",
        updated_at=utc_now_iso(),
    )
    save_task(workspace_root, updated)
    if run_to_finish is not None:
        _release_lock(
            workspace_root,
            task=updated,
            expected_stage="planning",
            run_id=run_to_finish.run_id,
            target_stage="plan_review",
            event_name="stage.completed",
            extra_data={"plan_version": version},
            delete_only=True,
        )
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        updated.id,
        "plan.proposed",
        {"plan_version": version, "generation_reason": "after_questions"},
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    return _lifecycle_payload(
        "plan regenerate",
        updated,
        warnings=[],
        changed=True,
        plan_version=version,
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
    required_for_plan: bool = False,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
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
        required_for_plan=required_for_plan,
        asked_by_actor=actor or _default_actor(),
        asked_in_harness=harness or _default_harness(),
    )
    save_question(workspace_root, question)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "question.added",
        {"question_id": question.id, "required_for_plan": required_for_plan},
    )
    return question


def answer_question(
    workspace_root: Path,
    task_ref: str,
    question_id: str,
    *,
    text: str,
    actor: ActorRef | None = None,
    answer_source: str = "user",
) -> QuestionRecord:
    task = resolve_task(workspace_root, task_ref)
    _enforce_decision(
        question_mutation_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            actor_role="user",
        )
    )
    stripped = text.strip()
    if not stripped:
        raise _cli_error(
            "Answer text must not be empty.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    question = resolve_question(workspace_root, task.id, question_id)
    answered = replace(
        question,
        status="answered",
        answer=stripped,
        answered_at=utc_now_iso(),
        answered_by=(actor.actor_name if actor is not None else "user"),
        answered_by_actor=actor or ActorRef(actor_type="user", actor_name="user"),
        answer_source=answer_source,
    )
    save_question(workspace_root, answered)
    _append_event(
        resolve_v2_paths(workspace_root).project_dir,
        task.id,
        "question.answered",
        {"question_id": answered.id},
    )
    return answered


def answer_questions(
    workspace_root: Path,
    task_ref: str,
    answers: Mapping[str, str],
    *,
    actor: ActorRef | None = None,
    answer_source: str = "harness",
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    if not answers:
        raise _cli_error("At least one answer is required.", EXIT_CODE_BAD_INPUT)
    known = {item.id: item for item in list_questions(workspace_root, task.id)}
    unknown = [question_id for question_id in answers if question_id not in known]
    if unknown:
        raise _cli_error(
            "Unknown question ids: " + ", ".join(unknown),
            EXIT_CODE_MISSING,
        )
    empty = [question_id for question_id, text in answers.items() if not text.strip()]
    if empty:
        raise _cli_error(
            "Answer text must not be empty for: " + ", ".join(empty),
            EXIT_CODE_BAD_INPUT,
        )
    answered_ids: list[str] = []
    answered_questions: list[dict[str, object]] = []
    for question_id, text in answers.items():
        question = answer_question(
            workspace_root,
            task.id,
            question_id,
            text=text,
            actor=actor,
            answer_source=answer_source,
        )
        answered_ids.append(question.id)
        answered_questions.append(question.to_dict())
    status = question_status(workspace_root, task.id)
    return {
        "kind": "question_answer_many",
        "task_id": task.id,
        "answered_question_ids": answered_ids,
        "answered": answered_questions,
        "required_open": status["required_open"],
        "required_open_questions": status["required_open_questions"],
        "plan_regeneration_needed": status["plan_regeneration_needed"],
        "next_action": status["next_action"],
    }


def question_status(workspace_root: Path, task_ref: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    questions = list_questions(workspace_root, task.id)
    required_open = _required_open_question_ids(questions)
    answered = [item for item in questions if item.status == "answered"]
    latest_plan = _latest_plan_or_none(workspace_root, task.id)
    answered_since_latest_plan = (
        _stale_answer_question_ids(questions, latest_plan)
        if latest_plan is not None
        else [item.id for item in answered]
    )
    regeneration_needed = bool(answered_since_latest_plan) and not required_open
    return {
        "kind": "question_status",
        "task_id": task.id,
        "required_open": len(required_open),
        "required_open_questions": required_open,
        "answered": len([item for item in questions if item.status == "answered"]),
        "answered_since_latest_plan": answered_since_latest_plan,
        "plan_regeneration_needed": regeneration_needed,
        "next_action": (
            "taskledger plan upsert --from-answers --file plan.md"
            if regeneration_needed
            else (
                "taskledger question answer-many --file answers.yaml"
                if required_open
                else "taskledger plan propose --file plan.md"
            )
        ),
    }


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


def start_implementation(
    workspace_root: Path,
    task_ref: str,
    *,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> dict[str, object]:
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
    try:
        accepted_plan = resolve_plan(
            workspace_root,
            task.id,
            version=task.accepted_plan_version,
        )
    except LaunchError as exc:
        raise _cli_error(
            "Implementation requires a stored accepted plan record.",
            EXIT_CODE_APPROVAL_REQUIRED,
        ) from exc
    if accepted_plan.status != "accepted":
        raise _cli_error(
            "Implementation requires an accepted plan record.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    _ensure_dependencies_done(workspace_root, task)
    run = _start_run(
        workspace_root,
        task,
        run_type="implementation",
        stage="implementing",
        actor=actor,
        harness=harness,
    )
    updated = replace(
        resolve_task(workspace_root, task.id),
        latest_implementation_run=run.run_id,
        status_stage="implementing",
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
        replace(updated, status_stage=task.status_stage),
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
    artifact_refs: tuple[str, ...] = (),
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
        replace(
            run,
            change_refs=tuple([*run.change_refs, change.change_id]),
            artifact_refs=tuple([*run.artifact_refs, *artifact_refs]),
        ),
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


def scan_changes(
    workspace_root: Path,
    task_ref: str,
    *,
    from_git: bool,
    summary: str,
) -> CodeChangeRecord:
    if not from_git:
        raise _cli_error(
            "scan-changes currently requires --from-git.",
            EXIT_CODE_BAD_INPUT,
        )
    git_state = _git_change_state(workspace_root)
    diff_stat = "\n".join(
        [
            f"branch: {git_state['branch']}",
            "status:",
            git_state["status"] or "(clean)",
            "diff_stat:",
            git_state["diff_stat"] or "(no diff)",
        ]
    )
    return add_change(
        workspace_root,
        task_ref,
        path=".",
        kind="scan",
        summary=summary.strip() or "Scanned Git changes.",
        command="git branch --show-current && git status --short && git diff --stat",
        git_diff_stat=diff_stat,
    )


def run_planning_command(
    workspace_root: Path,
    task_ref: str,
    *,
    argv: tuple[str, ...],
) -> dict[str, object]:
    if not argv:
        raise _cli_error("plan command requires a command to run.", EXIT_CODE_BAD_INPUT)
    task = resolve_task(workspace_root, task_ref)
    run = _require_running_run(
        workspace_root,
        task,
        task.latest_planning_run,
        expected_type="planning",
    )
    _enforce_decision(
        plan_command_decision(
            task,
            _lock_for_mutation(workspace_root, task.id),
            run=run,
        )
    )
    completed = subprocess.run(
        list(argv),
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = _command_output(argv, completed.stdout, completed.stderr)
    artifact_ref: str | None = None
    if len(output) > 4000 or output.count("\n") > 50:
        artifact_ref = _write_command_artifact(
            workspace_root,
            task.id,
            run.run_id,
            output,
        )
    change = CodeChangeRecord(
        change_id=next_project_id(
            "change",
            [item.change_id for item in list_changes(workspace_root, task.id)],
        ),
        task_id=task.id,
        implementation_run=run.run_id,
        timestamp=utc_now_iso(),
        kind="command",
        path=".",
        summary=_command_summary(argv, completed.returncode, artifact_ref),
        command=shlex.join(argv),
        exit_code=completed.returncode,
    )
    save_change(workspace_root, change)
    save_run(
        workspace_root,
        replace(
            run,
            change_refs=tuple([*run.change_refs, change.change_id]),
            artifact_refs=tuple(
                [*run.artifact_refs, *((artifact_ref,) if artifact_ref else ())]
            ),
        ),
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
        {"change_id": change.change_id, "path": "."},
    )
    return {
        "kind": "planning_command",
        "task_id": change.task_id,
        "change": change.to_dict(),
        "exit_code": completed.returncode,
        "artifact_path": artifact_ref,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_implementation_command(
    workspace_root: Path,
    task_ref: str,
    *,
    argv: tuple[str, ...],
) -> dict[str, object]:
    if not argv:
        raise _cli_error(
            "implement command requires a command to run.", EXIT_CODE_BAD_INPUT
        )
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
            action="record implementation commands",
        )
    )
    completed = subprocess.run(
        list(argv),
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = _command_output(argv, completed.stdout, completed.stderr)
    artifact_ref: str | None = None
    if len(output) > 4000 or output.count("\n") > 50:
        artifact_ref = _write_command_artifact(
            workspace_root,
            task.id,
            run.run_id,
            output,
        )
    change = add_change(
        workspace_root,
        task_ref,
        path=".",
        kind="command",
        summary=_command_summary(argv, completed.returncode, artifact_ref),
        command=shlex.join(argv),
        exit_code=completed.returncode,
        artifact_refs=((artifact_ref,) if artifact_ref else ()),
    )
    return {
        "kind": "implementation_command",
        "task_id": change.task_id,
        "change": change.to_dict(),
        "exit_code": completed.returncode,
        "artifact_path": artifact_ref,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _build_todo_gate_report(
    workspace_root: Path, task: TaskRecord
) -> dict[str, object]:
    """Build a report of todo completion status for finish gate validation."""
    task = _task_with_sidecars(workspace_root, task)
    todos = task.todos
    open_todos = [
        todo.id
        for todo in todos
        if not todo.done
        and todo.status not in {"done", "skipped"}
        and (
            not todo.mandatory
            or todo.active_at is not None
            or todo.source == "plan"
            or todo.source_plan_id is not None
        )
    ]
    blockers = [
        {
            "kind": "todo_open",
            "ref": todo_id,
            "message": f"Todo {todo_id} is not done.",
            "command_hint": f'taskledger todo done {todo_id} --evidence "..."',
        }
        for todo_id in open_todos
    ]
    return {
        "kind": "todo_gate_report",
        "task_id": task.id,
        "total": len(todos),
        "done": len(todos) - len(open_todos),
        "open_todos": open_todos,
        "blockers": blockers,
        "can_finish_implementation": not open_todos,
    }


def _require_todos_complete_for_implementation_finish(
    workspace_root: Path, task: TaskRecord
) -> None:
    """Enforce that all todos are done before finishing implementation."""
    report = _build_todo_gate_report(workspace_root, task)
    if report["can_finish_implementation"]:
        return
    error = LaunchError("Cannot finish implementation because todos are incomplete.")
    error.taskledger_exit_code = EXIT_CODE_VALIDATION_FAILED
    error.taskledger_error_code = "IMPLEMENTATION_TODOS_INCOMPLETE"
    error.taskledger_data = report
    raise error


def todo_status(workspace_root: Path, task_ref: str) -> dict[str, object]:
    """Get todo status and progress for a task."""
    task = resolve_task(workspace_root, task_ref)
    return _build_todo_gate_report(workspace_root, task)


def next_todo(workspace_root: Path, task_ref: str) -> dict[str, object]:
    """Get the next unfinished todo for a task."""
    task = _task_with_sidecars(workspace_root, resolve_task(workspace_root, task_ref))
    todos = task.todos

    # Prefer active todos first, then first open todo
    for todo in todos:
        if not todo.done and hasattr(todo, "status") and todo.status == "active":
            return {
                "kind": "next_todo",
                "task_id": task.id,
                "next_todo_id": todo.id,
                "next_todo": todo.to_dict(),
                "can_finish_implementation": False,
            }

    for todo in todos:
        if not todo.done:
            return {
                "kind": "next_todo",
                "task_id": task.id,
                "next_todo_id": todo.id,
                "next_todo": todo.to_dict(),
                "can_finish_implementation": False,
            }

    return {
        "kind": "next_todo",
        "task_id": task.id,
        "next_todo_id": None,
        "next_todo": None,
        "can_finish_implementation": True,
    }


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
    _require_todos_complete_for_implementation_finish(workspace_root, task)
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


def start_validation(
    workspace_root: Path,
    task_ref: str,
    *,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> dict[str, object]:
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
        actor=actor,
        harness=harness,
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


def _resolve_criterion_ref(plan: PlanRecord, criterion_ref: str) -> str:
    """Canonicalize criterion reference to the exact ID in the plan.

    Accepts:
    - exact ID: ac-0001
    - different case: AC-0001
    - short AC form: ac-1 (should match ac-0001)
    - numeric form: 1 (should match ac-0001)

    Raises LaunchError if criterion not found in plan.
    """
    if not plan.criteria:
        raise _cli_error(
            "No acceptance criteria defined in plan.",
            EXIT_CODE_BAD_INPUT,
        )

    normalized_ref = criterion_ref.strip().lower()

    for c in plan.criteria:
        c_id_lower = c.id.lower()

        if c_id_lower == normalized_ref:
            return c.id

        parts = c_id_lower.split("-")
        if len(parts) == 2:
            prefix, number = parts

            if normalized_ref == f"{prefix}-{number}":
                return c.id

            ref_parts = normalized_ref.split("-")
            if len(ref_parts) == 2:
                ref_prefix, ref_number = ref_parts
                if ref_prefix == prefix:
                    try:
                        if int(ref_number) == int(number):
                            return c.id
                    except ValueError:
                        pass

            if normalized_ref == number:
                return c.id

            try:
                if int(normalized_ref) == int(number):
                    return c.id
            except ValueError:
                pass

    criterion_ids = ", ".join(sorted(c.id for c in plan.criteria))
    raise _cli_error(
        f"Unknown acceptance criterion: {criterion_ref}.\n"
        f"Known criteria: {criterion_ids}.",
        EXIT_CODE_BAD_INPUT,
    )


def _build_validation_gate_report(
    workspace_root: Path,
    task: TaskRecord,
    run: TaskRunRecord | None = None,
) -> dict[str, object]:
    """Build a comprehensive validation gate report.

    Returns a dict with:
    - accepted_plan status
    - implementation run status
    - criteria satisfaction (latest-check-wins)
    - open mandatory todos
    - dependency blockers
    - can_finish_passed flag
    - blocker list with hints
    """
    run = run or _optional_run(workspace_root, task, task.latest_validation_run)

    report: dict[str, Any] = {
        "kind": "validation_status",
        "task_id": task.id,
        "task_slug": task.slug,
        "status_stage": task.status_stage,
        "active_stage": None,
        "run_id": run.run_id if run else None,
        "can_finish_passed": False,
    }

    report["accepted_plan"] = {}
    if task.accepted_plan_version is not None:
        accepted_plan = resolve_plan(
            workspace_root,
            task.id,
            version=task.accepted_plan_version,
        )
        report["accepted_plan"] = {
            "version": task.accepted_plan_version,
            "status": accepted_plan.status,
        }

    report["implementation"] = {}
    impl_run = _optional_run(workspace_root, task, task.latest_implementation_run)
    if impl_run:
        report["implementation"] = {
            "run_id": impl_run.run_id,
            "status": impl_run.status,
            "satisfied": impl_run.status == "finished",
        }

    report["criteria"] = []
    missing_criteria = []
    failing_criteria = []

    if task.accepted_plan_version is not None:
        accepted_plan = resolve_plan(
            workspace_root,
            task.id,
            version=task.accepted_plan_version,
        )

        checks_by_criterion: dict[str, list[ValidationCheck]] = {}
        if run:
            for check in run.checks:
                if check.criterion_id is not None:
                    checks_by_criterion.setdefault(check.criterion_id, []).append(check)

        for criterion in accepted_plan.criteria:
            checks = checks_by_criterion.get(criterion.id, [])

            latest_check = checks[-1] if checks else None
            latest_status = latest_check.status if latest_check else "not_run"
            satisfied = latest_status == "pass" or (
                latest_check and _criterion_has_user_waiver(latest_check)
            )

            has_waiver = latest_check and _criterion_has_user_waiver(latest_check)

            blocker = []
            if criterion.mandatory:
                if latest_status == "fail":
                    blocker = [
                        {"kind": "criterion_fail", "message": "Latest check failed"}
                    ]
                    failing_criteria.append(criterion.id)
                elif latest_status == "not_run":
                    blocker = [
                        {
                            "kind": "criterion_missing",
                            "message": "No passing check recorded",
                        }
                    ]
                    missing_criteria.append(criterion.id)
                elif not satisfied and latest_status != "pass":
                    blocker = [
                        {
                            "kind": "criterion_unsatisfied",
                            "message": f"Latest check status: {latest_status}",
                        }
                    ]
                    missing_criteria.append(criterion.id)

            criterion_report = {
                "id": criterion.id,
                "text": criterion.text,
                "mandatory": criterion.mandatory,
                "latest_check_id": latest_check.id if latest_check else None,
                "latest_status": latest_status,
                "satisfied": satisfied,
                "has_waiver": has_waiver,
                "evidence": list(latest_check.evidence) if latest_check else [],
                "history": [{"check_id": c.id, "status": c.status} for c in checks],
                "blockers": blocker,
            }
            report["criteria"].append(criterion_report)

    report["todos"] = {"open_mandatory": []}
    todos = load_todos(workspace_root, task.id).todos
    open_todos = [todo.id for todo in todos if todo.mandatory and not todo.done]
    report["todos"]["open_mandatory"] = open_todos

    report["dependencies"] = {"blockers": _dependency_blockers(workspace_root, task)}

    report["blockers"] = []
    blockers: list[dict[str, object]] = []

    if task.accepted_plan_version is None:
        blockers.append(
            {
                "kind": "no_accepted_plan",
                "message": "No accepted plan is recorded.",
                "command_hint": (
                    "taskledger plan propose ... && taskledger plan approve ..."
                ),
            }
        )
    elif task.accepted_plan_version is not None:
        accepted_plan = resolve_plan(
            workspace_root,
            task.id,
            version=task.accepted_plan_version,
        )
        if accepted_plan.status != "accepted":
            blockers.append(
                {
                    "kind": "plan_not_accepted",
                    "message": (
                        f"Accepted plan record status is "
                        f"{accepted_plan.status}, not accepted."
                    ),
                }
            )

    if not impl_run or impl_run.status != "finished":
        blockers.append(
            {
                "kind": "no_finished_implementation",
                "message": "No finished implementation run is recorded.",
                "command_hint": (
                    "taskledger implement start ... && taskledger implement finish ..."
                ),
            }
        )

    for missing_id in missing_criteria:
        blockers.append(
            {
                "kind": "criterion_missing",
                "ref": missing_id,
                "message": f"Mandatory criterion {missing_id} has no passing check.",
                "command_hint": (
                    f"taskledger validate check "
                    f"--criterion {missing_id} --status pass "
                    f'--evidence "..."'
                ),
            }
        )

    for failing_id in failing_criteria:
        blockers.append(
            {
                "kind": "criterion_fail",
                "ref": failing_id,
                "message": f"Mandatory criterion {failing_id} has a failing check.",
                "command_hint": (
                    f"taskledger validate check "
                    f"--criterion {failing_id} --status pass "
                    f'--evidence "..."'
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

    for dep_blocker in cast(list[str], report["dependencies"]["blockers"]):
        blockers.append(
            {
                "kind": "dependency_blocker",
                "ref": dep_blocker,
                "message": f"Dependency {dep_blocker} blocks this task.",
            }
        )

    report["blockers"] = blockers
    report["can_finish_passed"] = len(blockers) == 0

    return report


def validation_status(
    workspace_root: Path,
    task_ref: str,
    *,
    run_id: str | None = None,
) -> dict[str, object]:
    """Get validation status report for a task."""
    task = resolve_task(workspace_root, task_ref)
    run = None
    if run_id:
        from taskledger.storage.v2 import resolve_run

        run = resolve_run(workspace_root, task.id, run_id)

    report = _build_validation_gate_report(workspace_root, task, run)
    return {"kind": "validation_status", "result": report}


def add_validation_check(
    workspace_root: Path,
    task_ref: str,
    *,
    name: str | None = None,
    criterion_id: str | None = None,
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
    normalized_status = normalize_validation_check_status(status)
    check_id = f"check-{len(run.checks) + 1:04d}"
    resolved_criterion = criterion_id.strip() if criterion_id else None
    if normalized_status != "not_run" and resolved_criterion is None:
        raise _cli_error(
            "Validation checks must reference --criterion unless status is not_run.",
            EXIT_CODE_BAD_INPUT,
        )

    if resolved_criterion is not None:
        if task.accepted_plan_version is None:
            raise _cli_error(
                "Cannot add criterion check without an accepted plan. "
                "Accept a plan first with: task accept-plan",
                EXIT_CODE_BAD_INPUT,
            )
        accepted_plan = resolve_plan(
            workspace_root,
            task.id,
            version=task.accepted_plan_version,
        )
        resolved_criterion = _resolve_criterion_ref(accepted_plan, resolved_criterion)

    check = ValidationCheck(
        name=(name or resolved_criterion or check_id).strip(),
        id=check_id,
        criterion_id=resolved_criterion,
        status=normalized_status,
        details=details.strip() if details else None,
        evidence=tuple(item.strip() for item in evidence if item.strip()),
    )
    updated = replace(run, checks=tuple([*run.checks, check]))
    save_run(workspace_root, updated)
    return updated


def waive_criterion(
    workspace_root: Path,
    task_ref: str,
    *,
    criterion_id: str,
    reason: str,
    actor_name: str | None = None,
) -> TaskRunRecord:
    """Record a criterion waiver for a validation check."""
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

    if task.accepted_plan_version is None:
        raise _cli_error(
            "Cannot waive criterion without an accepted plan.",
            EXIT_CODE_BAD_INPUT,
        )

    accepted_plan = resolve_plan(
        workspace_root,
        task.id,
        version=task.accepted_plan_version,
    )
    resolved_criterion = _resolve_criterion_ref(accepted_plan, criterion_id)

    if not reason.strip():
        raise _cli_error("Waiver reason is required.", EXIT_CODE_BAD_INPUT)

    waiver = CriterionWaiver(
        actor=ActorRef(
            actor_type="user",
            actor_name=(actor_name or getpass.getuser() or "user").strip(),
            tool="manual",
        ),
        reason=reason.strip(),
    )

    check_id = f"check-{len(run.checks) + 1:04d}"
    check = ValidationCheck(
        name=resolved_criterion,
        id=check_id,
        criterion_id=resolved_criterion,
        status="pass",
        waiver=waiver,
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
    if normalized_result == "passed":
        _ensure_validation_can_pass(workspace_root, task, run)
    target_stage: TaskStatusStage = (
        "done" if normalized_result == "passed" else "failed_validation"
    )
    if normalized_result == "passed":
        run_status = "finished"
    elif normalized_result == "blocked":
        run_status = "blocked"
    else:
        run_status = "failed"
    finished = replace(
        run,
        status=cast(
            Literal[
                "running",
                "paused",
                "finished",
                "passed",
                "failed",
                "blocked",
                "aborted",
            ],
            run_status,
        ),
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
        raise _cli_error(
            "No active lock exists for the task. "
            "This is normal after plan propose, implement finish, or validate finish. "
            "Run `taskledger next-action` to see what to do next.",
            EXIT_CODE_MISSING,
        )
    broken_lock = replace(
        lock,
        broken_at=utc_now_iso(),
        broken_by=_default_actor(),
        broken_reason=reason.strip(),
    )
    audit_path = _write_broken_lock_audit(paths, task.id, broken_lock)
    _append_event(
        paths.project_dir,
        task.id,
        "lock.broken",
        {
            "lock_id": lock.lock_id,
            "reason": reason,
            "audit_path": str(audit_path.relative_to(paths.project_dir)),
        },
    )
    _append_event(
        paths.project_dir,
        task.id,
        "repair.lock_broken",
        {
            "lock_id": lock.lock_id,
            "reason": reason,
            "audit_path": str(audit_path.relative_to(paths.project_dir)),
        },
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
        "lock": broken_lock.to_dict(),
        "reason": reason,
        "audit_path": str(audit_path.relative_to(paths.project_dir)),
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
    runs = list_runs(workspace_root, task.id)
    active_stage = _task_active_stage(
        workspace_root,
        task,
        lock=lock,
        runs=runs,
    )
    action: str
    reason: str
    blockers: list[dict[str, object]] = []
    if active_stage == "planning":
        questions = list_questions(workspace_root, task.id)
        open_questions = _required_open_question_ids(questions)
        answered_questions = [
            item.id
            for item in questions
            if item.status == "answered" and item.required_for_plan
        ]
        if open_questions:
            action, reason = (
                "question-answer",
                "Required planning questions are open.",
            )
            blockers.append(
                {
                    "kind": "open_questions",
                    "question_ids": open_questions,
                    "message": "Required planning questions must be answered.",
                }
            )
        elif answered_questions:
            action, reason = (
                "plan-regenerate",
                "Answered planning questions should be reflected in the plan.",
            )
        else:
            action, reason = (
                "plan-propose",
                "Planning is active; propose the next plan.",
            )
    elif active_stage == "implementation":
        # During implementation, prioritize todos if any are open
        todo_report = _build_todo_gate_report(workspace_root, task)
        open_todo_count = len(cast(list[object], todo_report.get("open_todos", [])))
        if open_todo_count > 0:
            action, reason = (
                "todo-work",
                f"Implementation is in progress; {open_todo_count} todos remain.",
            )
        else:
            action, reason = (
                "implement-finish",
                "All todos done; ready to finish implementation.",
            )
    elif active_stage == "validation":
        action, reason = "validate-finish", "Validation is in progress."
        gate_report = _build_validation_gate_report(workspace_root, task)
        report_blockers = cast(list[dict[str, object]], gate_report.get("blockers", []))
        for blocker in report_blockers:
            blockers.append(
                {
                    "kind": str(blocker.get("kind", "validation")),
                    "message": str(
                        blocker.get("message", "Validation gate not satisfied")
                    ),
                }
            )
    elif task.status_stage == "draft":
        action, reason = "plan", "Draft tasks need planning before work starts."
    elif task.status_stage == "plan_review":
        questions = list_questions(workspace_root, task.id)
        open_questions = _required_open_question_ids(questions)
        latest_plan = _latest_plan_or_none(workspace_root, task.id)
        stale_answers = (
            _stale_answer_question_ids(questions, latest_plan)
            if latest_plan is not None
            else []
        )
        if open_questions:
            action, reason = (
                "question-answer",
                "Required planning questions are open.",
            )
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
            blockers.append(
                {
                    "kind": "stale_answers",
                    "question_ids": stale_answers,
                    "message": "Regenerate the plan from answered questions.",
                }
            )
        else:
            action, reason = "plan-approve", "A proposed plan is waiting for review."
    elif task.status_stage == "approved":
        action, reason = "implement", "The approved plan is ready for implementation."
        if task.accepted_plan_version is None:
            blockers.append(
                {"kind": "approval", "message": "No accepted plan version is recorded."}
            )
        blockers.extend(
            cast(list[dict[str, object]], _dependency_blockers(workspace_root, task))
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
    elif task.status_stage == "failed_validation":
        action, reason = "implement", "Validation failed; return to implementation."
        blockers.extend(
            cast(list[dict[str, object]], _dependency_blockers(workspace_root, task))
        )
    elif task.status_stage == "done":
        action, reason = "none", "The task is complete."
    else:
        action, reason = "none", "The task is cancelled."
    if lock is not None and active_stage is None:
        blockers.append(
            {
                "kind": "lock",
                "message": (
                    f"Task has a {lock.stage} lock from {lock.run_id} "
                    "without a matching running run."
                ),
            }
        )
    return {
        "kind": "task_next_action",
        "task_id": task.id,
        "status_stage": task.status_stage,
        "active_stage": active_stage,
        "action": action,
        "reason": reason,
        "blocking": blockers,
        "next_command": _next_action_command(action),
    }


def can_perform(workspace_root: Path, task_ref: str, action: str) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    lock = _current_lock(workspace_root, task.id)
    active_stage = _task_active_stage(workspace_root, task, lock=lock)
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
                        f"Task has an active {lock.stage} lock from {lock.run_id}."
                    ),
                }
            )
    elif action == "implement":
        ok = (
            task.status_stage in IMPLEMENTABLE_TASK_STAGES
            and task.accepted_plan_version is not None
            and not _dependency_blockers(workspace_root, task)
            and lock is None
            and active_stage is None
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
                        f"Task has an active {lock.stage} lock from {lock.run_id}."
                    ),
                }
            )
    elif action == "validate":
        impl_run = _optional_run(workspace_root, task, task.latest_implementation_run)
        ok = (
            task.status_stage == "implemented"
            and lock is None
            and active_stage is None
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
                        f"Task has an active {lock.stage} lock from {lock.run_id}."
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
        "active_stage": active_stage,
        "blocking": blocking,
    }


def task_dossier(
    workspace_root: Path,
    task_ref: str,
    *,
    format_name: str = "markdown",
) -> str | dict[str, object]:
    from taskledger.services.handoff import render_handoff

    return render_handoff(
        workspace_root,
        task_ref,
        mode="full",
        format_name=format_name,
    )


def reindex(workspace_root: Path) -> dict[str, object]:
    paths = ensure_v2_layout(workspace_root)
    counts = rebuild_v2_indexes(paths)
    _append_event(
        paths.project_dir, "*", "repair.index", dict(cast(dict[str, object], counts))
    )
    return {"kind": "taskledger_reindex", "counts": counts}


def repair_task_record(
    workspace_root: Path,
    task_ref: str,
    *,
    reason: str,
) -> dict[str, object]:
    if not reason.strip():
        raise _cli_error("Task repair requires --reason.", EXIT_CODE_BAD_INPUT)
    task = resolve_task(workspace_root, task_ref)
    paths = resolve_v2_paths(workspace_root)
    _append_event(
        paths.project_dir,
        task.id,
        "repair.task",
        {"reason": reason.strip()},
    )
    return {
        "kind": "task_repair",
        "task_id": task.id,
        "changed": False,
        "reason": reason.strip(),
    }


def list_events(workspace_root: Path) -> list[dict[str, object]]:
    events_dir = resolve_v2_paths(workspace_root).events_dir
    return [item.to_dict() for item in load_events(events_dir)]


def _start_run(
    workspace_root: Path,
    task: TaskRecord,
    *,
    run_type: str,
    stage: str,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> TaskRunRecord:
    existing_lock = _current_lock(workspace_root, task.id)
    if existing_lock is not None:
        if lock_is_expired(existing_lock):
            raise _stale_lock_error(task.id, existing_lock)
        raise _cli_error(
            _lock_conflict_message(task.id, existing_lock),
            EXIT_CODE_LOCK_CONFLICT,
        )
    running_runs = [
        item for item in list_runs(workspace_root, task.id) if item.status == "running"
    ]
    if running_runs:
        raise _cli_error(
            f"Task {task.id} already has a running {running_runs[0].run_type} run.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    resolved_actor = actor or _default_actor()
    run = TaskRunRecord(
        run_id=next_project_id(
            "run",
            [item.run_id for item in list_runs(workspace_root, task.id)],
        ),
        task_id=task.id,
        run_type=normalize_run_type(run_type),
        actor=resolved_actor,
        harness=harness,
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
        actor=resolved_actor,
        harness=harness,
    )
    return run


def _acquire_lock(
    workspace_root: Path,
    *,
    task: TaskRecord,
    stage: str,
    run: TaskRunRecord,
    reason: str,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> TaskLock:
    if stage not in ACTIVE_TASK_STAGES:
        raise _cli_error("Only active stages can acquire locks.", EXIT_CODE_BAD_INPUT)
    paths = resolve_v2_paths(workspace_root)
    lock_path = task_lock_path(paths, task.id)
    existing = read_lock(lock_path)
    if existing is not None:
        if lock_is_expired(existing):
            raise _stale_lock_error(task.id, existing)
        if existing.run_id == run.run_id:
            return existing
        raise _cli_error(
            _lock_conflict_message(task.id, existing), EXIT_CODE_LOCK_CONFLICT
        )
    now = datetime.now(timezone.utc)
    resolved_actor = actor or _default_actor()
    lock = TaskLock(
        lock_id=_next_lock_id(workspace_root, now),
        task_id=task.id,
        stage=cast(Literal["planning", "implementing", "validating"], stage),
        run_id=run.run_id,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(hours=2)).isoformat(),
        lease_seconds=7200,
        last_heartbeat_at=now.isoformat(),
        reason=reason,
        holder=resolved_actor,
        actor=resolved_actor,
        harness=harness,
    )
    try:
        write_lock(lock_path, lock)
    except LaunchError as exc:
        raise _cli_error(
            _lock_conflict_message(task.id, read_lock(lock_path) or lock),
            EXIT_CODE_LOCK_CONFLICT,
        ) from exc
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
    for requirement in load_requirements(workspace_root, task.id).requirements:
        if _has_user_waiver(requirement.waiver):
            continue
        required = resolve_task(workspace_root, requirement.task_id)
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
        raise _stale_lock_error(task_id, lock)
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
        raise _stale_lock_error(task_id, lock)
    return lock


def _dependency_blockers(
    workspace_root: Path, task: TaskRecord
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for requirement in load_requirements(workspace_root, task.id).requirements:
        if _has_user_waiver(requirement.waiver):
            continue
        required = resolve_task(workspace_root, requirement.task_id)
        if required.status_stage != "done":
            blockers.append(
                {
                    "kind": "dependency",
                    "message": (
                        f"Requirement {required.id} is still {required.status_stage}."
                    ),
                }
            )
    return blockers


def _lock_conflict_message(task_id: str, lock: TaskLock) -> str:
    if lock_is_expired(lock):
        return (
            f"Task {task_id} has an expired {lock.stage} lock from {lock.run_id}. "
            "Break it explicitly with: "
            f'taskledger lock break --task {task_id} --reason "..."'
        )
    return f"Task {task_id} is locked by {lock.run_id} for {lock.stage}."


def _enforce_decision(decision: Decision) -> None:
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


def _default_harness() -> HarnessRef:
    return HarnessRef(
        harness_id="harness-unknown",
        name=os.getenv("TASKLEDGER_HARNESS") or "unknown",
        kind="unknown",
        session_id=os.getenv("TASKLEDGER_SESSION_ID"),
        working_directory=os.getcwd(),
    )


def _append_event(
    project_dir: Path,
    task_id: str,
    event_name: str,
    data: dict[str, object],
) -> None:
    timestamp = utc_now_iso()
    append_event(
        project_dir / "events",
        TaskEvent(
            ts=timestamp,
            event=event_name,
            task_id=task_id,
            actor=_default_actor(),
            harness=_default_harness(),
            event_id=next_event_id(project_dir / "events", timestamp),
            data=data,
        ),
    )


def _summary_line(text: str | None) -> str | None:
    if text is None:
        return None
    stripped = " ".join(text.split())
    return stripped[:117] + "..." if len(stripped) > 120 else stripped


def _git_change_state(workspace_root: Path) -> dict[str, str]:
    inside = _run_command(
        workspace_root,
        ("git", "rev-parse", "--is-inside-work-tree"),
        not_git_message="Git change scan requires a Git work tree.",
    )
    if inside.strip() != "true":
        raise _cli_error(
            "Git change scan requires a Git work tree.", EXIT_CODE_BAD_INPUT
        )
    branch = _run_command(workspace_root, ("git", "branch", "--show-current")).strip()
    status = _run_command(workspace_root, ("git", "status", "--short")).strip()
    diff_stat = _run_command(workspace_root, ("git", "diff", "--stat")).strip()
    return {
        "branch": branch or "(detached)",
        "status": status,
        "diff_stat": diff_stat,
    }


def _run_command(
    workspace_root: Path,
    argv: tuple[str, ...],
    *,
    not_git_message: str | None = None,
) -> str:
    completed = subprocess.run(
        list(argv),
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return completed.stdout
    if not_git_message and "not a git repository" in completed.stderr.lower():
        raise _cli_error(not_git_message, EXIT_CODE_BAD_INPUT)
    raise _cli_error(
        completed.stderr.strip() or f"Command failed: {' '.join(argv)}",
        EXIT_CODE_GENERIC_FAILURE,
    )


def _command_output(
    argv: tuple[str, ...],
    stdout: str,
    stderr: str,
) -> str:
    return (
        f"$ {shlex.join(argv)}\n\n"
        f"stdout:\n{stdout or '(empty)'}\n\n"
        f"stderr:\n{stderr or '(empty)'}\n"
    )


def _command_summary(
    argv: tuple[str, ...],
    exit_code: int,
    artifact_ref: str | None,
) -> str:
    summary = f"Ran {shlex.join(argv)} (exit {exit_code})"
    if artifact_ref is not None:
        summary += f" output: @{artifact_ref}"
    return summary


def _write_command_artifact(
    workspace_root: Path,
    task_id: str,
    run_id: str,
    output: str,
) -> str:
    paths = resolve_v2_paths(workspace_root)
    artifact_dir = task_artifacts_dir(paths, task_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    index = len(list(artifact_dir.glob(f"{run_id}-command-*.log"))) + 1
    artifact_path = artifact_dir / f"{run_id}-command-{index:04d}.log"
    atomic_write_text(artifact_path, output)
    return str(artifact_path.relative_to(paths.project_dir))


def _parse_plan_front_matter(body: str) -> tuple[dict[str, object], str]:
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, body
    for index in range(1, len(lines)):
        if lines[index].strip() != "---":
            continue
        front_matter = yaml.safe_load("\n".join(lines[1:index])) or {}
        if not isinstance(front_matter, dict):
            raise _cli_error(
                "Plan front matter must be a YAML mapping.",
                EXIT_CODE_BAD_INPUT,
            )
        return front_matter, "\n".join(lines[index + 1 :])
    raise _cli_error("Unterminated plan front matter.", EXIT_CODE_BAD_INPUT)


def _criteria_from_plan_input(
    front_matter: dict[str, object],
    criteria: tuple[str, ...],
) -> tuple[AcceptanceCriterion, ...]:
    raw_criteria = front_matter.get("acceptance_criteria", front_matter.get("criteria"))
    items: list[AcceptanceCriterion] = []
    if raw_criteria is not None:
        if not isinstance(raw_criteria, list):
            raise _cli_error(
                "Plan criteria front matter must be a list.",
                EXIT_CODE_BAD_INPUT,
            )
        for index, item in enumerate(raw_criteria, start=1):
            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                items.append(AcceptanceCriterion(id=_criterion_id(index), text=text))
                continue
            if not isinstance(item, dict):
                raise _cli_error(
                    "Plan criteria must be strings or mappings.",
                    EXIT_CODE_BAD_INPUT,
                )
            text = str(item.get("text") or "").strip()
            if not text:
                # Accept single-key shorthand: {ac-0001: "some text"}
                if len(item) == 1:
                    criterion_key, text_value = next(iter(item.items()))
                    text = str(text_value).strip()
                    if not text:
                        raise _cli_error(
                            "Plan criteria mappings must include non-empty text.",
                            EXIT_CODE_BAD_INPUT,
                        )
                    items.append(
                        AcceptanceCriterion(
                            id=str(criterion_key).strip(),
                            text=text,
                            mandatory=True,
                        )
                    )
                    continue
                raise _cli_error(
                    "Plan criteria mappings must include text.",
                    EXIT_CODE_BAD_INPUT,
                )
            criterion_id = str(item.get("id") or _criterion_id(index)).strip()
            items.append(
                AcceptanceCriterion(
                    id=criterion_id,
                    text=text,
                    mandatory=bool(item.get("mandatory", True)),
                )
            )
    else:
        for index, item in enumerate(criteria, start=1):
            text = item.strip()
            if text:
                items.append(AcceptanceCriterion(id=_criterion_id(index), text=text))
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise _cli_error("Plan criteria ids must be unique.", EXIT_CODE_BAD_INPUT)
    return tuple(items)


def _todos_from_plan_input(front_matter: dict[str, object]) -> tuple[TaskTodo, ...]:
    raw_todos = front_matter.get("todos")
    if raw_todos is None:
        return ()
    if not isinstance(raw_todos, list):
        raise _cli_error("Plan todos front matter must be a list.", EXIT_CODE_BAD_INPUT)
    items: list[TaskTodo] = []
    for index, item in enumerate(raw_todos, start=1):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            items.append(
                TaskTodo(
                    id=f"plan-todo-{index:04d}",
                    text=text,
                    mandatory=True,
                    source="plan",
                )
            )
            continue
        if not isinstance(item, dict):
            raise _cli_error(
                "Plan todos must be strings or mappings.",
                EXIT_CODE_BAD_INPUT,
            )
        text = str(item.get("text") or "").strip()
        if not text:
            raise _cli_error(
                "Plan todo mappings must include text.",
                EXIT_CODE_BAD_INPUT,
            )
        items.append(
            TaskTodo(
                id=str(
                    item.get("id") or item.get("id_hint") or f"plan-todo-{index:04d}"
                ),
                text=text,
                mandatory=bool(item.get("mandatory", True)),
                source="plan",
                validation_hint=_optional_string_value(item.get("validation_hint")),
            )
        )
    return tuple(items)


def _answer_snapshot_hash(questions: list[QuestionRecord]) -> str | None:
    answered = [
        f"{item.id}\0{item.answer or ''}"
        for item in questions
        if item.status == "answered"
    ]
    if not answered:
        return None
    digest = hashlib.sha256("\n".join(sorted(answered)).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _required_open_question_ids(questions: list[QuestionRecord]) -> list[str]:
    return [
        item.id
        for item in questions
        if item.status == "open" and item.required_for_plan
    ]


def _latest_plan_or_none(workspace_root: Path, task_id: str) -> PlanRecord | None:
    plans = list_plans(workspace_root, task_id)
    return plans[-1] if plans else None


def _stale_answer_question_ids(
    questions: list[QuestionRecord],
    plan: PlanRecord,
) -> list[str]:
    answered = [
        item
        for item in questions
        if item.status == "answered" and item.required_for_plan
    ]
    if not answered:
        return []
    current_hash = _answer_snapshot_hash(questions)
    if (
        plan.generation_reason == "after_questions"
        and plan.based_on_answer_hash == current_hash
    ):
        return []
    return [item.id for item in answered]


def _next_action_command(action: str) -> str | None:
    return {
        "plan": "taskledger plan start",
        "plan-propose": "taskledger plan upsert --file plan.md",
        "question-answer": "taskledger question answer-many --file answers.yaml",
        "plan-regenerate": "taskledger plan upsert --from-answers --file plan.md",
        "plan-approve": "taskledger plan approve --version VERSION --actor user",
        "implement": "taskledger implement start",
        "todo-work": "taskledger implement checklist",
        "implement-finish": "taskledger implement finish --summary SUMMARY",
        "validate": "taskledger validate start",
        "validate-finish": (
            "taskledger validate finish --result passed --summary SUMMARY"
        ),
    }.get(action)


def _normalize_todo_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _optional_front_matter_string(
    front_matter: dict[str, object],
    key: str,
) -> str | None:
    return _optional_string_value(front_matter.get(key))


def _optional_string_value(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _criterion_id(index: int) -> str:
    return f"ac-{index:04d}"


def _normalize_local_id(ref: str, prefix: str) -> str:
    raw_prefix = f"{prefix}-"
    if not ref.startswith(raw_prefix):
        return ref
    suffix = ref.removeprefix(raw_prefix)
    if not suffix.isdigit():
        return ref
    return f"{prefix}-{int(suffix):04d}"


def _next_lock_id(workspace_root: Path, now: datetime) -> str:
    paths = resolve_v2_paths(workspace_root)
    prefix = now.strftime("lock-%Y%m%dT%H%M%SZ")
    existing = [item.lock_id for item in load_active_locks(workspace_root)]
    existing.extend(
        path.stem.removeprefix("broken-")
        for path in paths.tasks_dir.glob("task-*/audit/broken-lock-*.yaml")
    )
    sequence = sum(1 for item in existing if item.startswith(prefix)) + 1
    return f"{prefix}-{sequence:04d}"


def _has_user_waiver(waiver: DependencyWaiver | None) -> bool:
    return waiver is not None and waiver.actor.actor_type == "user"


def _ensure_validation_can_pass(
    workspace_root: Path,
    task: TaskRecord,
    run: TaskRunRecord,
) -> None:
    report = _build_validation_gate_report(workspace_root, task, run)

    if not cast(bool, report["can_finish_passed"]):
        blockers = cast(list[dict[str, object]], report["blockers"])
        missing_criteria = []
        failing_criteria = []
        open_todos = []
        dependency_blockers = []

        for blocker in blockers:
            kind = blocker.get("kind")
            if kind == "criterion_missing":
                missing_criteria.append(blocker.get("ref"))
            elif kind == "criterion_fail":
                failing_criteria.append(blocker.get("ref"))
            elif kind == "todo_open":
                open_todos.append(blocker.get("ref"))
            elif kind == "dependency_blocker":
                dependency_blockers.append(blocker.get("ref"))

        raise _validation_incomplete(
            "Cannot mark validation passed because "
            "mandatory validation gates are incomplete.",
            {
                "missing_criteria": missing_criteria,
                "failing_criteria": failing_criteria,
                "open_mandatory_todos": open_todos,
                "dependency_blockers": dependency_blockers,
                "blockers": blockers,
            },
        )


def _criterion_has_user_waiver(check: ValidationCheck) -> bool:
    return check.waiver is not None and check.waiver.actor.actor_type == "user"


def _validation_incomplete(message: str, details: dict[str, object]) -> LaunchError:
    error = LaunchError(message)
    error.taskledger_exit_code = EXIT_CODE_VALIDATION_FAILED
    error.taskledger_error_code = "VALIDATION_INCOMPLETE"
    error.taskledger_data = details
    return error


def _render_validation_status(payload: dict[str, object]) -> str:  # noqa: C901
    """Render the validation gate report in human-readable text."""
    lines: list[str] = []

    task_slug = payload.get("task_slug", payload.get("task_id", "unknown"))
    task_id = payload.get("task_id", "")
    lines.append(f"# Validation Status: {task_slug}")
    if task_id:
        lines.append(f"Task ID: {task_id}")
    lines.append("")

    status_stage = payload.get("status_stage", "unknown")
    run_id = payload.get("run_id")
    lines.append(f"**Status Stage:** {status_stage}")
    if run_id:
        lines.append(f"**Run ID:** {run_id}")
    lines.append("")

    active_stage = payload.get("active_stage")
    if active_stage:
        lines.append(f"**Active Stage:** {active_stage}")
        lines.append("")

    accepted_plan = payload.get("accepted_plan", {})
    if isinstance(accepted_plan, dict):
        if accepted_plan:
            plan_version = accepted_plan.get("version")
            plan_status = accepted_plan.get("status", "unknown")
            lines.append(
                f"**Accepted Plan:** Version {plan_version}, Status: {plan_status}"
            )
        else:
            lines.append("**Accepted Plan:** None")
    lines.append("")

    implementation = payload.get("implementation", {})
    if isinstance(implementation, dict):
        if implementation:
            impl_run_id = implementation.get("run_id")
            impl_status = implementation.get("status", "unknown")
            impl_satisfied = implementation.get("satisfied", False)
            lines.append(
                f"**Implementation:** Run {impl_run_id}, Status: {impl_status}"
            )
            lines.append(f"  Satisfied: {'✓' if impl_satisfied else '✗'}")
        else:
            lines.append("**Implementation:** None")
    lines.append("")

    criteria = cast(list[dict[str, object]], payload.get("criteria", []))
    if criteria:
        lines.append("## Acceptance Criteria")
        for criterion in criteria:
            if isinstance(criterion, dict):
                criterion_id = criterion.get("id", "unknown")
                text = str(criterion.get("text", ""))
                mandatory = criterion.get("mandatory", False)
                satisfied = criterion.get("satisfied", False)
                has_waiver = criterion.get("has_waiver", False)
                latest_status = criterion.get("latest_status", "unknown")

                checkbox = "☒" if satisfied else "☐"
                mandatory_marker = " (mandatory)" if mandatory else ""
                lines.append(f"  {checkbox} {criterion_id}{mandatory_marker}")
                if text:
                    lines.append(f"      {text[:80]}...")
                lines.append(f"      Status: {latest_status}")
                if has_waiver:
                    lines.append("      ✓ Waived")
        lines.append("")

    todos_obj = payload.get("todos", {})
    if isinstance(todos_obj, dict):
        open_todos = todos_obj.get("open_mandatory", [])
        if open_todos:
            lines.append("## Open Mandatory Todos")
            for todo_id in open_todos:
                lines.append(f"  - {todo_id}")
            lines.append("")

    dependencies_obj = payload.get("dependencies", {})
    if isinstance(dependencies_obj, dict):
        dep_blockers = dependencies_obj.get("blockers", [])
        if dep_blockers:
            lines.append("## Dependency Blockers")
            for blocker_id in dep_blockers:
                lines.append(f"  - {blocker_id}")
            lines.append("")

    can_finish_passed = payload.get("can_finish_passed", False)
    lines.append("## Result")
    lines.append(f"**Can Finish Passed:** {'✓ Yes' if can_finish_passed else '✗ No'}")

    blockers = cast(list[dict[str, object]], payload.get("blockers", []))
    if blockers and not can_finish_passed:
        lines.append("")
        lines.append("### Blocking Issues")
        for blocker in blockers:
            if isinstance(blocker, dict):
                kind = blocker.get("kind", "unknown")
                message = blocker.get("message", "")
                lines.append(f"  - **{kind}**: {message}")
                hint = blocker.get("command_hint")
                if hint:
                    lines.append(f"    Hint: `{hint}`")

    return "\n".join(lines)


def _approval_actor(
    *,
    actor_type: str,
    actor_name: str | None,
    note: str | None,
    allow_agent_approval: bool,
    reason: str | None,
) -> ActorRef:
    normalized_actor = actor_type.strip()
    if normalized_actor == "user":
        if not (note or "").strip():
            raise _cli_error("Plan approval requires --note.", EXIT_CODE_BAD_INPUT)
        return ActorRef(
            actor_type="user",
            actor_name=(actor_name or getpass.getuser() or "user").strip(),
            tool="manual",
        )
    if normalized_actor == "agent":
        if not allow_agent_approval or not (reason or "").strip():
            raise _cli_error(
                "Agent approval requires --allow-agent-approval and --reason.",
                EXIT_CODE_APPROVAL_REQUIRED,
            )
        return ActorRef(
            actor_type="agent",
            actor_name=(actor_name or getpass.getuser() or "taskledger").strip(),
            tool="taskledger",
            host=socket.gethostname(),
            pid=os.getpid(),
        )
    raise _cli_error(
        f"Unsupported approval actor: {actor_type}",
        EXIT_CODE_BAD_INPUT,
    )


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
    active_stage = (
        derive_active_stage(lock, (run,))
        if lock is not None and run is not None
        else None
    )
    payload: dict[str, object] = {
        "ok": True,
        "command": command,
        "task_id": task.id,
        "status": task.status_stage,
        "status_stage": task.status_stage,
        "active_stage": active_stage,
        "changed": changed,
        "warnings": warnings,
        "lock": lock.to_dict() if lock is not None else None,
    }
    if plan_version is not None:
        payload["plan_version"] = plan_version
    if run is not None:
        payload["run_id"] = run.run_id
        payload["run"] = run.to_dict()
    if result is not None:
        payload["result"] = result
    return payload


def _cli_error(message: str, exit_code: int) -> LaunchError:
    error = LaunchError(message)
    error.taskledger_exit_code = exit_code
    return error


def _stale_lock_error(task_id: str, lock: TaskLock) -> LaunchError:
    error = LaunchError(
        f"Task {task_id} has an expired {lock.stage} lock from {lock.run_id}. "
        "Break it explicitly before continuing."
    )
    error.taskledger_exit_code = EXIT_CODE_STALE_LOCK_REQUIRES_BREAK
    error.taskledger_error_type = "StaleLockRequiresBreak"
    error.taskledger_remediation = [
        (
            f"taskledger lock break --task {task_id} "
            f'--reason "recover stale {lock.stage} lock"'
        )
    ]
    error.taskledger_data = {
        "task_id": task_id,
        "lock": lock.to_dict(),
    }
    return error


def _task_with_sidecars(workspace_root: Path, task: TaskRecord) -> TaskRecord:
    return replace(
        task,
        requirements=_task_requirements(workspace_root, task),
        file_links=load_links(workspace_root, task.id).links,
        todos=load_todos(workspace_root, task.id).todos,
    )


def _task_payload(task: TaskRecord, *, active_stage: str | None) -> dict[str, object]:
    payload = task.to_dict()
    payload["active_stage"] = active_stage
    return payload


def _active_task_payload(
    workspace_root: Path,
    task: TaskRecord,
    *,
    state: ActiveTaskState,
    changed: bool,
    previous_task_id: str | None,
    active: bool = True,
) -> dict[str, object]:
    return {
        "kind": "active_task",
        "task_id": task.id,
        "slug": task.slug,
        "title": task.title,
        "status_stage": task.status_stage,
        "active_stage": _task_active_stage(workspace_root, task) if active else None,
        "active": active,
        "changed": changed,
        "previous_task_id": previous_task_id,
        "state": state.to_dict(),
    }


def _actor_for_active_task(actor_type: str) -> ActorRef:
    if actor_type not in {"agent", "user", "system"}:
        raise _cli_error(
            f"Unsupported actor type: {actor_type}",
            EXIT_CODE_BAD_INPUT,
        )
    base = _default_actor()
    return replace(
        base,
        actor_type=cast(Literal["agent", "user", "system"], actor_type),
    )


def _ensure_active_switch_allowed(
    workspace_root: Path,
    task_id: str,
    *,
    force: bool,
    reason: str | None,
) -> None:
    lock = _current_lock(workspace_root, task_id)
    if lock is None or lock_is_expired(lock):
        return
    if force and reason and reason.strip():
        return
    raise LockConflict(
        f"Active task {task_id} has a live {lock.stage} lock from {lock.run_id}. "
        "Pass --force with --reason to switch or clear the active task.",
        task_id=task_id,
        details={"lock": lock.to_dict()},
        remediation=[
            f"taskledger lock show --task {task_id}",
            (
                'Pass --force --reason "..." only if you intend to leave '
                "the lock in place."
            ),
        ],
    )


def _task_active_stage(
    workspace_root: Path,
    task: TaskRecord,
    *,
    lock: TaskLock | None = None,
    runs: list[TaskRunRecord] | None = None,
) -> str | None:
    current_lock = lock or _current_lock(workspace_root, task.id)
    if current_lock is None or lock_is_expired(current_lock):
        return None
    task_runs = runs if runs is not None else list_runs(workspace_root, task.id)
    return derive_active_stage(current_lock, task_runs)


def _task_requirements(workspace_root: Path, task: TaskRecord) -> tuple[str, ...]:
    return tuple(
        item.task_id for item in load_requirements(workspace_root, task.id).requirements
    )


def _write_broken_lock_audit(paths: V2Paths, task_id: str, lock: TaskLock) -> Path:
    timestamp = lock.broken_at or utc_now_iso()
    filename = timestamp.replace(":", "").replace("-", "").replace("+00:00", "Z")
    path = task_audit_dir(paths, task_id) / f"broken-lock-{filename}.yaml"
    atomic_write_text(
        path,
        yaml.safe_dump(lock.to_dict(), sort_keys=False, allow_unicode=True),
    )
    return path
