from __future__ import annotations

from taskledger.storage.common import write_json
from taskledger.storage.v2 import (
    V2Paths,
    list_introductions,
    list_tasks,
    load_active_locks,
    load_requirements,
)


def rebuild_v2_indexes(paths: V2Paths) -> dict[str, int]:
    tasks = list_tasks(paths.workspace_root)
    introductions = list_introductions(paths.workspace_root)
    locks = load_active_locks(paths.workspace_root)
    dependencies = [
        {
            "task_id": task.id,
            "requirements": [
                item.task_id
                for item in load_requirements(
                    paths.workspace_root, task.id
                ).requirements
            ],
        }
        for task in tasks
    ]
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
        "introductions": len(introductions),
        "locks": len(locks),
        "dependencies": len(dependencies),
    }
