from __future__ import annotations

from typing import cast
from pathlib import Path

from taskledger.domain.policies import derive_active_stage
from taskledger.storage.events import load_events
from taskledger.storage.locks import lock_is_expired
from taskledger.storage.v2 import (
    ensure_v2_layout,
    list_changes,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    load_requirements,
    load_todos,
    resolve_introduction,
    resolve_run,
)


def inspect_v2_project(workspace_root: Path) -> dict[str, object]:  # noqa: C901
    ensure_v2_layout(workspace_root)
    tasks = list_tasks(workspace_root)
    task_map = {task.id: task for task in tasks}
    locks = load_active_locks(workspace_root)
    errors: list[str] = []
    warnings: list[str] = []
    repair_hints: list[str] = []
    broken_links: list[dict[str, object]] = []
    expired_locks: list[dict[str, object]] = []

    task_runs = {task.id: list_runs(workspace_root, task.id) for task in tasks}
    run_map = {
        (task_id, run.run_id): run
        for task_id, runs in task_runs.items()
        for run in runs
    }

    for task in tasks:
        plans = list_plans(workspace_root, task.id)
        accepted = [plan for plan in plans if plan.status == "accepted"]
        if task.introduction_ref:
            try:
                resolve_introduction(workspace_root, task.introduction_ref)
            except Exception:
                broken_links.append(
                    {
                        "task_id": task.id,
                        "kind": "introduction",
                        "ref": task.introduction_ref,
                    }
                )
        for requirement in (
            item.task_id for item in load_requirements(workspace_root, task.id).requirements
        ):
            if requirement not in task_map:
                broken_links.append(
                    {"task_id": task.id, "kind": "requirement", "ref": requirement}
                )
        if task.accepted_plan_version is not None and not any(
            plan.plan_version == task.accepted_plan_version for plan in plans
        ):
            errors.append(
                f"Task {task.id} points to missing accepted plan "
                f"v{task.accepted_plan_version}."
            )
        if len(accepted) > 1:
            errors.append(f"Task {task.id} has multiple accepted plans.")
        if task.accepted_plan_version is not None and len(accepted) != 1:
            errors.append(
                f"Task {task.id} must have exactly one accepted plan "
                "for accepted_plan_version."
            )
        todos = load_todos(workspace_root, task.id).todos
        if len({todo.id for todo in todos}) != len(todos):
            errors.append(f"Task {task.id} contains duplicate todo ids.")

        active_lock = next(
            (
                lock
                for lock in locks
                if lock.task_id == task.id and not lock_is_expired(lock)
            ),
            None,
        )
        running_runs = [run for run in task_runs[task.id] if run.status == "running"]
        if task.status_stage in {"planning", "implementing", "validating"}:
            errors.append(
                f"Task {task.id} persists transient stage {task.status_stage} as status."
            )
        if len(running_runs) > 1:
            errors.append(f"Task {task.id} has multiple running runs.")
        active_stage = derive_active_stage(active_lock, running_runs)
        if running_runs and active_stage is None:
            errors.append(
                f"Task {task.id} has a running run without a matching active lock."
            )
            repair_hints.append(
                "Inspect the run/lock pair and either repair it or break the lock "
                f"for task {task.id} explicitly."
            )
        if active_lock is not None and active_stage is None and not running_runs:
            errors.append(
                f"Task {task.id} has a {active_lock.stage} lock without a running run."
            )
            repair_hints.append(
                "Break the stale lock with "
                f"`taskledger lock break {task.id} --reason \"...\"`."
            )

        for change in list_changes(workspace_root, task.id):
            run = run_map.get((task.id, change.implementation_run))
            if run is None:
                errors.append(
                    f"Change {change.change_id} references missing "
                    f"implementation run {change.implementation_run}."
                )
            elif run.run_type != "implementation":
                errors.append(
                    f"Change {change.change_id} references "
                    f"non-implementation run {change.implementation_run}."
                )

        for run in task_runs[task.id]:
            if run.run_type == "validation" and run.based_on_implementation_run:
                linked = run_map.get((task.id, run.based_on_implementation_run))
                if linked is None:
                    errors.append(
                        f"Validation run {run.run_id} references missing "
                        "implementation run "
                        f"{run.based_on_implementation_run}."
                    )
                elif linked.run_type != "implementation":
                    errors.append(
                        f"Validation run {run.run_id} references "
                        "non-implementation run "
                        f"{run.based_on_implementation_run}."
                    )

    for lock in locks:
        lock_task = task_map.get(lock.task_id)
        if lock_task is None:
            errors.append(
                f"Lock {lock.lock_id} references missing task {lock.task_id}."
            )
            continue
        try:
            if lock_is_expired(lock):
                expired_locks.append(lock.to_dict())
        except Exception as exc:
            errors.append(str(exc))
        try:
            run = resolve_run(workspace_root, lock.task_id, lock.run_id)
        except Exception:
            errors.append(
                f"Lock {lock.lock_id} references missing run {lock.run_id} "
                f"for task {lock.task_id}."
            )
            continue
        if run.status != "running":
            errors.append(f"Lock {lock.lock_id} references non-running run {run.run_id}.")
        expected_stage = {
            "planning": "planning",
            "implementation": "implementing",
            "validation": "validating",
        }[run.run_type]
        if lock.stage != expected_stage:
            errors.append(
                f"Lock {lock.lock_id} stage {lock.stage} does not match "
                f"run {run.run_id} type {run.run_type}."
            )

    if broken_links:
        errors.append("V2 task records contain broken references.")
    if expired_locks:
        warnings.append("Expired task locks require explicit resolution.")
        repair_hints.append(
            "Break stale locks explicitly with "
            "`taskledger lock break <task> --reason \"...\"`."
        )

    return {
        "kind": "taskledger_doctor",
        "counts": {
            "tasks": len(tasks),
            "plans": sum(len(list_plans(workspace_root, task.id)) for task in tasks),
            "questions": sum(
                len(list_questions(workspace_root, task.id)) for task in tasks
            ),
            "runs": sum(len(task_runs[task.id]) for task in tasks),
            "changes": sum(
                len(list_changes(workspace_root, task.id)) for task in tasks
            ),
            "locks": len(locks),
        },
        "healthy": not errors,
        "errors": errors,
        "warnings": warnings,
        "repair_hints": repair_hints,
        "broken_links": broken_links,
        "expired_locks": expired_locks,
    }


def inspect_v2_locks(workspace_root: Path) -> dict[str, object]:
    payload = inspect_v2_project(workspace_root)
    expired_locks = list(cast(list[object], payload["expired_locks"]))
    return {
        "kind": "taskledger_lock_inspection",
        "healthy": not expired_locks,
        "expired_locks": expired_locks,
    }


def inspect_v2_schema(workspace_root: Path) -> dict[str, object]:
    payload = inspect_v2_project(workspace_root)
    schema_errors = [
        item for item in cast(list[str], payload["errors"]) if "schema" in item.lower() or "version" in item.lower()
    ]
    return {
        "kind": "taskledger_schema_inspection",
        "healthy": not schema_errors,
        "errors": schema_errors,
    }


def inspect_v2_indexes(workspace_root: Path) -> dict[str, object]:
    paths = ensure_v2_layout(workspace_root)
    missing = [
        str(path.relative_to(paths.project_dir))
        for path in (
            paths.tasks_index_path,
            paths.active_locks_index_path,
            paths.dependencies_index_path,
            paths.introductions_index_path,
            paths.latest_runs_index_path,
            paths.plan_versions_index_path,
        )
        if not path.exists()
    ]
    event_errors: list[str] = []
    try:
        load_events(paths.events_dir)
    except Exception as exc:
        event_errors.append(str(exc))
    return {
        "kind": "taskledger_index_inspection",
        "healthy": not missing and not event_errors,
        "missing_indexes": missing,
        "event_errors": event_errors,
    }
