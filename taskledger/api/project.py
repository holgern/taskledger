from __future__ import annotations

from pathlib import Path
from typing import cast

from taskledger.domain.policies import derive_active_stage
from taskledger.exchange import (
    export_project_payload,
    import_project_payload,
    parse_project_import_payload,
    write_project_snapshot,
)
from taskledger.services.doctor_v2 import inspect_v2_project
from taskledger.storage.init import init_project_state
from taskledger.storage.locks import lock_is_expired
from taskledger.storage.paths import resolve_project_paths
from taskledger.storage.v2 import (
    list_changes,
    list_introductions,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    load_active_task_state,
    resolve_task,
)


def init_project(
    workspace_root: Path,
    *,
    taskledger_dir: Path | None = None,
) -> dict[str, object]:
    paths, created = init_project_state(workspace_root, taskledger_dir=taskledger_dir)
    return {
        "kind": "taskledger_init",
        "root": str(paths.project_dir),
        "project_dir": str(paths.project_dir),
        "workspace_root": str(paths.workspace_root),
        "config_path": str(paths.config_path),
        "taskledger_dir": str(paths.taskledger_dir),
        "created": created,
    }


def project_status_summary(workspace_root: Path) -> dict[str, object]:
    doctor = inspect_v2_project(workspace_root)
    paths = resolve_project_paths(workspace_root)
    return {
        "kind": "taskledger_status",
        "workspace_root": str(paths.workspace_root),
        "config_path": str(paths.config_path),
        "taskledger_dir": str(paths.taskledger_dir),
        "project_dir": str(paths.project_dir),
        "counts": _project_counts(workspace_root),
        "healthy": bool(doctor["healthy"]),
        "active_task": _active_task_status(workspace_root),
    }


def project_status(workspace_root: Path) -> dict[str, object]:
    doctor = inspect_v2_project(workspace_root)
    tasks = list_tasks(workspace_root)
    locks = load_active_locks(workspace_root)
    paths = resolve_project_paths(workspace_root)
    return {
        "kind": "taskledger_status",
        "workspace_root": str(paths.workspace_root),
        "config_path": str(paths.config_path),
        "taskledger_dir": str(paths.taskledger_dir),
        "project_dir": str(paths.project_dir),
        "counts": _project_counts(workspace_root),
        "healthy": bool(doctor["healthy"]),
        "active_task": _active_task_status(workspace_root),
        "errors": list(cast(list[object], doctor["errors"])),
        "warnings": list(cast(list[object], doctor["warnings"])),
        "repair_hints": list(cast(list[object], doctor["repair_hints"])),
        "tasks": [
            {
                "id": task.id,
                "slug": task.slug,
                "title": task.title,
                "status": task.status_stage,
                "status_stage": task.status_stage,
                "active_stage": derive_active_stage(
                    next(
                        (
                            lock
                            for lock in locks
                            if lock.task_id == task.id and not lock_is_expired(lock)
                        ),
                        None,
                    ),
                    list_runs(workspace_root, task.id),
                ),
                "accepted_plan_version": task.accepted_plan_version,
                "latest_plan_version": task.latest_plan_version,
            }
            for task in tasks
        ],
        "doctor": doctor,
    }


def project_doctor(workspace_root: Path) -> dict[str, object]:
    return inspect_v2_project(workspace_root)


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


def _project_counts(workspace_root: Path) -> dict[str, int]:
    tasks = list_tasks(workspace_root)
    return {
        "tasks": len(tasks),
        "introductions": len(list_introductions(workspace_root)),
        "plans": sum(len(list_plans(workspace_root, task.id)) for task in tasks),
        "questions": sum(
            len(list_questions(workspace_root, task.id)) for task in tasks
        ),
        "runs": sum(len(list_runs(workspace_root, task.id)) for task in tasks),
        "changes": sum(len(list_changes(workspace_root, task.id)) for task in tasks),
        "locks": len(load_active_locks(workspace_root)),
    }


def _active_task_status(workspace_root: Path) -> dict[str, object] | None:
    state = load_active_task_state(workspace_root)
    if state is None:
        return None
    task = resolve_task(workspace_root, state.task_id)
    return {
        "task_id": task.id,
        "slug": task.slug,
        "title": task.title,
        "status_stage": task.status_stage,
    }
