from __future__ import annotations

from taskledger.domain.policies import derive_active_stage
from taskledger.storage.common import write_json
from taskledger.storage.locks import lock_is_expired
from taskledger.storage.v2 import (
    V2Paths,
    list_introductions,
    list_plans,
    list_runs,
    list_tasks,
    load_active_locks,
    load_requirements,
)


def rebuild_v2_indexes(paths: V2Paths) -> dict[str, int]:
    tasks = list_tasks(paths.workspace_root)
    introductions = list_introductions(paths.workspace_root)
    locks = load_active_locks(paths.workspace_root)
    locks_by_task = {
        lock.task_id: lock for lock in locks if not lock_is_expired(lock)
    }
    plan_versions = []
    latest_runs = []
    runs_by_task = {
        task.id: list_runs(paths.workspace_root, task.id)
        for task in tasks
    }
    dependencies = [
        {
            "task_id": task.id,
            "requirements": [
                item.task_id
                for item in load_requirements(paths.workspace_root, task.id).requirements
            ],
        }
        for task in tasks
    ]
    for task in tasks:
        plans = list_plans(paths.workspace_root, task.id)
        runs = runs_by_task[task.id]
        plan_versions.append(
            {
                "task_id": task.id,
                "latest_plan_version": task.latest_plan_version,
                "accepted_plan_version": task.accepted_plan_version,
                "plans": [
                    {
                        "plan_version": plan.plan_version,
                        "status": plan.status,
                        "supersedes": plan.supersedes,
                    }
                    for plan in plans
                ],
            }
        )
        latest_runs.append(
            {
                "task_id": task.id,
                "latest_planning_run": task.latest_planning_run,
                "latest_implementation_run": task.latest_implementation_run,
                "latest_validation_run": task.latest_validation_run,
                "runs": [
                    {
                        "run_id": run.run_id,
                        "run_type": run.run_type,
                        "status": run.status,
                        "result": run.result,
                    }
                    for run in runs
                ],
            }
        )
    write_json(
        paths.tasks_index_path,
        [
            {
                "id": task.id,
                "slug": task.slug,
                "title": task.title,
                "status": task.status_stage,
                "status_stage": task.status_stage,
                "active_stage": derive_active_stage(
                    locks_by_task.get(task.id),
                    runs_by_task[task.id],
                ),
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
    write_json(paths.latest_runs_index_path, latest_runs)
    write_json(paths.plan_versions_index_path, plan_versions)
    return {
        "tasks": len(tasks),
        "introductions": len(introductions),
        "locks": len(locks),
        "dependencies": len(dependencies),
        "latest_runs": len(latest_runs),
        "plan_versions": len(plan_versions),
    }
