from __future__ import annotations

from pathlib import Path
from typing import cast

from taskledger.domain.policies import derive_active_stage
from taskledger.domain.states import TASKLEDGER_STORAGE_LAYOUT_VERSION
from taskledger.storage.events import load_events
from taskledger.storage.locks import lock_is_expired
from taskledger.storage.migrations import inspect_records_for_migration
from taskledger.storage.paths import (
    DEFAULT_TASKLEDGER_DIR_NAME,
    PROJECT_CONFIG_FILENAMES,
    load_project_locator,
    resolve_project_paths,
)
from taskledger.storage.project_config import load_project_config_document
from taskledger.storage.task_store import (
    ensure_v2_layout,
    list_changes,
    list_handoffs_with_errors,
    list_plans,
    list_questions,
    list_runs,
    list_tasks,
    load_active_locks,
    load_active_task_state,
    load_requirements,
    load_todos,
    resolve_introduction,
    resolve_run,
    task_dir,
)


def inspect_v2_project(workspace_root: Path) -> dict[str, object]:  # noqa: C901
    resolved_paths = resolve_project_paths(workspace_root)
    locator = load_project_locator(workspace_root)
    errors: list[str] = []
    warnings: list[str] = []
    repair_hints: list[str] = []
    config_candidates = [
        resolved_paths.workspace_root / filename
        for filename in PROJECT_CONFIG_FILENAMES
    ]
    if all(candidate.exists() for candidate in config_candidates):
        warnings.append(
            "Both taskledger.toml and .taskledger.toml exist; using .taskledger.toml."
        )
    if (
        locator.source == "legacy"
        and (resolved_paths.taskledger_dir / "project.toml").exists()
    ):
        warnings.append(
            "Legacy config location: .taskledger/project.toml. "
            "Move it to taskledger.toml before release."
        )
    if resolved_paths.config_path.exists():
        try:
            load_project_config_document(resolved_paths.config_path)
        except Exception as exc:
            errors.append(str(exc))
    if not resolved_paths.taskledger_dir.exists():
        errors.append(
            "Configured taskledger_dir does not exist: "
            f"{resolved_paths.taskledger_dir}."
        )
    storage_meta_path = resolved_paths.taskledger_dir / "storage.yaml"
    if resolved_paths.taskledger_dir.exists() and not storage_meta_path.exists():
        errors.append(
            f"Missing storage.yaml in taskledger_dir: {resolved_paths.taskledger_dir}."
        )
    nested_storage_dir = resolved_paths.taskledger_dir / DEFAULT_TASKLEDGER_DIR_NAME
    if (
        resolved_paths.taskledger_dir
        != resolved_paths.workspace_root / DEFAULT_TASKLEDGER_DIR_NAME
        and nested_storage_dir.exists()
    ):
        warnings.append(
            "Configured taskledger_dir contains a nested .taskledger directory."
        )
        repair_hints.append(
            "Move taskledger state to the configured root and remove the nested "
            ".taskledger directory."
        )

    ensure_v2_layout(workspace_root)
    tasks = list_tasks(workspace_root)
    task_map = {task.id: task for task in tasks}
    locks = load_active_locks(workspace_root)
    broken_links: list[dict[str, object]] = []
    expired_locks: list[dict[str, object]] = []

    task_runs = {task.id: list_runs(workspace_root, task.id) for task in tasks}
    run_map = {
        (task_id, run.run_id): run
        for task_id, runs in task_runs.items()
        for run in runs
    }

    try:
        active_state = load_active_task_state(workspace_root)
    except Exception as exc:
        active_state = None
        errors.append(f"Active task state is invalid: {exc}")
    if active_state is not None:
        active_task = task_map.get(active_state.task_id)
        if active_task is None:
            errors.append(f"Active task points to missing task {active_state.task_id}.")
        elif active_task.status_stage in {"cancelled", "done"}:
            warnings.append(
                f"Active task {active_task.id} is {active_task.status_stage}."
            )

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
            item.task_id
            for item in load_requirements(workspace_root, task.id).requirements
        ):
            if requirement not in task_map:
                broken_links.append(
                    {"task_id": task.id, "kind": "requirement", "ref": requirement}
                )
        _handoffs, handoff_errors = list_handoffs_with_errors(workspace_root, task.id)
        errors.extend(handoff_errors)
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
                f"Task {task.id} persists transient stage "
                f"{task.status_stage} as status."
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
                f'`taskledger lock break --task {task.id} --reason "..."`.'
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
            errors.append(
                f"Lock {lock.lock_id} references non-running run {run.run_id}."
            )
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

    # Detect orphan slug directories (empty dirs matching task slugs but not task-NNNN)
    task_slugs = {task.slug for task in tasks if task.slug}
    paths = ensure_v2_layout(workspace_root)
    for child in paths.tasks_dir.iterdir():
        if (
            child.is_dir()
            and not child.name.startswith("task-")
            and child.name in task_slugs
            and not (child / "task.md").exists()
        ):
            is_empty = not any(child.iterdir())
            if is_empty:
                warnings.append(f"Orphan empty slug directory: {child.name}/")
                repair_hints.append(
                    "Remove orphan directory with `taskledger repair task-dirs`."
                )
            else:
                warnings.append(
                    f"Legacy slug sidecar directory retained: {child.name}/"
                )

    # Detect unsupported pre-release legacy YAML sidecars.
    legacy_sidecar_found = False
    for task in tasks:
        sidecar_dirs = [task_dir(paths, task.id)]
        if task.slug and task.slug != task.id:
            sidecar_dirs.append(paths.tasks_dir / task.slug)
        for sidecar_dir in sidecar_dirs:
            for legacy_name in ("todos.yaml", "links.yaml", "requirements.yaml"):
                legacy_path = sidecar_dir / legacy_name
                if not legacy_path.exists():
                    continue
                legacy_sidecar_found = True
                warnings.append(
                    f"Unsupported pre-release legacy sidecar retained: {legacy_path}."
                )
    if legacy_sidecar_found:
        repair_hints.append(
            "Run a one-off migration script for pre-release sidecars or remove the "
            "legacy YAML sidecars after confirming their contents are obsolete."
        )

    if broken_links:
        errors.append("V2 task records contain broken references.")
    if expired_locks:
        warnings.append("Expired task locks require explicit resolution.")
        repair_hints.append(
            "Break stale locks explicitly with "
            '`taskledger lock break <task> --reason "..."`.'
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
            "active_task": 1 if active_state is not None else 0,
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
    try:
        payload = inspect_v2_project(workspace_root)
        schema_errors = [
            item
            for item in cast(list[str], payload["errors"])
            if "schema" in item.lower() or "version" in item.lower()
        ]
    except Exception as exc:
        schema_errors = [str(exc)]
    needed, issues = inspect_records_for_migration(workspace_root)
    schema_errors.extend(issue.message for issue in issues)
    schema_errors.extend(
        (
            f"{item.object_type} record requires schema migration "
            f"{item.current_version} -> {item.target_version}: {item.path}"
        )
        for item in needed
    )
    # Check storage.yaml layout version
    try:
        from taskledger.storage.meta import read_storage_meta

        meta = read_storage_meta(workspace_root)
        if meta is None:
            schema_errors.append(
                "Missing storage.yaml."
                " Run 'taskledger init' or 'taskledger migrate apply'."
            )
        elif meta.storage_layout_version > TASKLEDGER_STORAGE_LAYOUT_VERSION:
            schema_errors.append(
                f"Storage layout {meta.storage_layout_version} is newer than "
                f"supported {TASKLEDGER_STORAGE_LAYOUT_VERSION}. Upgrade taskledger."
            )
        elif meta.storage_layout_version < TASKLEDGER_STORAGE_LAYOUT_VERSION:
            schema_errors.append(
                f"Storage layout {meta.storage_layout_version}"
                " requires migration to"
                f" {TASKLEDGER_STORAGE_LAYOUT_VERSION}."
                " Run 'taskledger migrate apply --backup'."
            )
    except Exception as exc:
        schema_errors.append(f"Cannot read storage.yaml: {exc}")

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
            paths.active_locks_index_path,
            paths.dependencies_index_path,
            paths.introductions_index_path,
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


def cleanup_orphan_slug_dirs(workspace_root: Path) -> dict[str, object]:
    """Remove empty slug-named directories under tasks/ that have no task.md."""
    paths = ensure_v2_layout(workspace_root)
    tasks = list_tasks(workspace_root)
    task_slugs = {task.slug for task in tasks if task.slug}
    removed: list[str] = []
    for child in sorted(paths.tasks_dir.iterdir()):
        if (
            child.is_dir()
            and not child.name.startswith("task-")
            and child.name in task_slugs
            and not (child / "task.md").exists()
            and not any(child.iterdir())
        ):
            child.rmdir()
            removed.append(child.name)
    return {
        "kind": "taskledger_repair_task_dirs",
        "removed": removed,
        "count": len(removed),
    }
