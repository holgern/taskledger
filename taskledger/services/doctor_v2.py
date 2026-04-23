from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from taskledger.storage.v2 import (
    ensure_v2_layout,
    list_changes,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    resolve_introduction,
)


def inspect_v2_project(workspace_root: Path) -> dict[str, object]:
    ensure_v2_layout(workspace_root)
    tasks = list_tasks(workspace_root)
    errors: list[str] = []
    warnings: list[str] = []
    broken_links: list[dict[str, object]] = []
    expired_locks: list[dict[str, object]] = []
    for task in tasks:
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
        for requirement in task.requirements:
            try:
                next(item for item in tasks if item.id == requirement)
            except StopIteration:
                broken_links.append(
                    {"task_id": task.id, "kind": "requirement", "ref": requirement}
                )
        if task.latest_plan_version is not None:
            try:
                list_plans(workspace_root, task.id)
            except Exception:
                broken_links.append(
                    {
                        "task_id": task.id,
                        "kind": "plan",
                        "ref": str(task.latest_plan_version),
                    }
                )
    now = datetime.now(timezone.utc)
    for lock in load_active_locks(workspace_root):
        if lock.expires_at is None:
            continue
        try:
            expires = datetime.fromisoformat(lock.expires_at)
        except ValueError:
            continue
        if expires < now:
            expired_locks.append(lock.to_dict())
    if broken_links:
        errors.append("V2 task records contain broken references.")
    if expired_locks:
        warnings.append("Expired task locks require explicit resolution.")
    return {
        "kind": "taskledger_v2_doctor",
        "counts": {
            "tasks": len(tasks),
            "plans": sum(len(list_plans(workspace_root, task.id)) for task in tasks),
            "questions": sum(
                len(list_questions(workspace_root, task.id)) for task in tasks
            ),
            "runs": sum(len(list_runs(workspace_root, task.id)) for task in tasks),
            "changes": sum(
                len(list_changes(workspace_root, task.id)) for task in tasks
            ),
            "locks": len(load_active_locks(workspace_root)),
        },
        "healthy": not errors,
        "errors": errors,
        "warnings": warnings,
        "broken_links": broken_links,
        "expired_locks": expired_locks,
    }
