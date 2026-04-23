from __future__ import annotations

from taskledger.storage.common import write_json
from taskledger.storage.v2 import (
    V2Paths,
    list_introductions,
    list_tasks,
    load_active_locks,
)


def rebuild_v2_indexes(paths: V2Paths) -> dict[str, int]:
    tasks = list_tasks(paths.workspace_root)
    introductions = list_introductions(paths.workspace_root)
    locks = load_active_locks(paths.workspace_root)
    dependencies = [
        {
            "task_id": task.id,
            "requirements": list(task.requirements),
        }
        for task in tasks
    ]
    write_json(
        paths.tasks_index_path,
        [
            {
                "id": task.id,
                "slug": task.slug,
                "title": task.title,
                "status_stage": task.status_stage,
                "accepted_plan_version": task.accepted_plan_version,
                "latest_plan_version": task.latest_plan_version,
            }
            for task in tasks
        ],
    )
    write_json(
        paths.introductions_index_path,
        [
            {"id": intro.id, "slug": intro.slug, "title": intro.title}
            for intro in introductions
        ],
    )
    write_json(paths.active_locks_index_path, [lock.to_dict() for lock in locks])
    write_json(paths.dependencies_index_path, dependencies)
    return {
        "tasks": len(tasks),
        "introductions": len(introductions),
        "locks": len(locks),
        "dependencies": len(dependencies),
    }
