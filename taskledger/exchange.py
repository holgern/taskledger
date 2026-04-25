from __future__ import annotations

import json
import shutil
from pathlib import Path

from taskledger.domain.models import (
    ActiveTaskState,
    CodeChangeRecord,
    IntroductionRecord,
    PlanRecord,
    QuestionRecord,
    TaskHandoffRecord,
    TaskEvent,
    TaskLock,
    TaskRecord,
    TaskRunRecord,
)
from taskledger.errors import LaunchError
from taskledger.models import utc_now_iso
from taskledger.storage.events import append_event, load_events
from taskledger.storage.indexes import rebuild_v2_indexes
from taskledger.storage.locks import write_lock
from taskledger.storage.v2 import (
    V2Paths,
    ensure_v2_layout,
    load_active_locks,
    load_active_task_state,
    overwrite_plan,
    plan_markdown_path,
    resolve_v2_paths,
    save_active_task_state,
    save_change,
    save_handoff,
    save_introduction,
    save_plan,
    save_question,
    save_run,
    save_task,
    task_lock_path,
)
from taskledger.storage.v2 import list_changes as list_v2_changes
from taskledger.storage.v2 import list_introductions as list_v2_introductions
from taskledger.storage.v2 import list_plans as list_v2_plans
from taskledger.storage.v2 import list_questions as list_v2_questions
from taskledger.storage.v2 import list_runs as list_v2_runs
from taskledger.storage.v2 import list_tasks as list_v2_tasks
from taskledger.storage.v2 import list_handoffs as list_v2_handoffs


def export_project_payload(
    workspace_root: Path,
    *,
    include_bodies: bool = False,
    include_run_artifacts: bool = False,
) -> dict[str, object]:
    v2_payload = _export_v2_payload(workspace_root)
    return {
        "kind": "taskledger_export",
        "version": 2,
        "schema_version": 2,
        "generated_at": utc_now_iso(),
        "project_dir": str(resolve_v2_paths(workspace_root).project_dir),
        "options": {
            "include_bodies": include_bodies,
            "include_run_artifacts": include_run_artifacts,
        },
        "counts": {
            key: len(_dict_list(value))
            for key, value in v2_payload.items()
            if isinstance(value, list)
        },
        "v2": v2_payload,
    }


def parse_project_import_payload(text: str, *, format_name: str) -> dict[str, object]:
    if format_name != "json":
        raise LaunchError(f"Unsupported project import format: {format_name}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Invalid project import JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LaunchError("Project import JSON must be an object.")
    result: dict[str, object] = payload
    if payload.get("success") is True and isinstance(payload.get("data"), dict):
        candidate = payload["data"]
        if candidate.get("kind") in {"taskledger_export", "project_export"}:
            result = candidate
    if payload.get("ok") is True and isinstance(payload.get("result"), dict):
        candidate = payload["result"]
        if candidate.get("kind") in {"taskledger_export", "project_export"}:
            result = candidate
    if result.get("kind") not in {None, "taskledger_export", "project_export"}:
        raise LaunchError("Unsupported project import payload kind.")
    return result


def import_project_payload(
    workspace_root: Path,
    *,
    payload: dict[str, object],
    replace: bool,
) -> dict[str, object]:
    paths = ensure_v2_layout(workspace_root)
    if replace:
        _clear_v2_state(paths)
    _import_v2_payload(workspace_root, payload)
    counts = rebuild_v2_indexes(paths)
    return {
        "kind": "taskledger_import",
        "replace": replace,
        "counts": counts,
    }


def write_project_snapshot(
    workspace_root: Path,
    *,
    output_dir: Path,
    include_bodies: bool,
    include_run_artifacts: bool,
) -> dict[str, object]:
    payload = export_project_payload(
        workspace_root,
        include_bodies=include_bodies,
        include_run_artifacts=include_run_artifacts,
    )
    timestamp = utc_now_iso().replace(":", "-").replace("+00:00", "Z")
    snapshot_dir = output_dir / f"taskledger-snapshot-{timestamp}"
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    export_path = snapshot_dir / "taskledger-export.json"
    export_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "kind": "taskledger_snapshot",
        "snapshot_dir": str(snapshot_dir),
        "export_path": str(export_path),
        "include_bodies": include_bodies,
        "include_run_artifacts": include_run_artifacts,
    }


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _export_v2_payload(workspace_root: Path) -> dict[str, object]:
    tasks = list_v2_tasks(workspace_root)
    introductions = list_v2_introductions(workspace_root)
    return {
        "tasks": [item.to_dict() for item in tasks],
        "active_task": (
            active_state.to_dict()
            if (active_state := load_active_task_state(workspace_root)) is not None
            else None
        ),
        "introductions": [item.to_dict() for item in introductions],
        "plans": [
            plan.to_dict()
            for task in tasks
            for plan in list_v2_plans(workspace_root, task.id)
        ],
        "questions": [
            question.to_dict()
            for task in tasks
            for question in list_v2_questions(workspace_root, task.id)
        ],
        "runs": [
            run.to_dict()
            for task in tasks
            for run in list_v2_runs(workspace_root, task.id)
        ],
        "changes": [
            change.to_dict()
            for task in tasks
            for change in list_v2_changes(workspace_root, task.id)
        ],
        "handoffs": [
            handoff.to_dict()
            for task in tasks
            for handoff in list_v2_handoffs(workspace_root, task.id)
        ],
        "locks": [item.to_dict() for item in load_active_locks(workspace_root)],
        "events": [
            item.to_dict()
            for item in load_events(resolve_v2_paths(workspace_root).events_dir)
        ],
    }


def _import_v2_payload(workspace_root: Path, payload: dict[str, object]) -> None:
    raw_v2 = payload.get("v2")
    if not isinstance(raw_v2, dict):
        raise LaunchError("Import payload is missing v2 task state.")
    paths = resolve_v2_paths(workspace_root)
    for item in _dict_list(raw_v2.get("tasks")):
        save_task(workspace_root, TaskRecord.from_dict(item))
    active_task = raw_v2.get("active_task")
    if active_task is not None:
        state = ActiveTaskState.from_dict(active_task)
        if not any(task.id == state.task_id for task in list_v2_tasks(workspace_root)):
            raise LaunchError(
                f"Import active task points to missing task: {state.task_id}"
            )
        save_active_task_state(workspace_root, state)
    for item in _dict_list(raw_v2.get("introductions")):
        save_introduction(workspace_root, IntroductionRecord.from_dict(item))
    for item in _dict_list(raw_v2.get("plans")):
        plan = PlanRecord.from_dict(item)
        if plan_markdown_path(paths, plan.task_id, plan.plan_version).exists():
            overwrite_plan(workspace_root, plan)
        else:
            save_plan(workspace_root, plan)
    for item in _dict_list(raw_v2.get("questions")):
        save_question(workspace_root, QuestionRecord.from_dict(item))
    for item in _dict_list(raw_v2.get("runs")):
        save_run(workspace_root, TaskRunRecord.from_dict(item))
    for item in _dict_list(raw_v2.get("changes")):
        save_change(workspace_root, CodeChangeRecord.from_dict(item))
    for item in _dict_list(raw_v2.get("handoffs")):
        save_handoff(workspace_root, TaskHandoffRecord.from_dict(item))
    for item in _dict_list(raw_v2.get("locks")):
        lock = TaskLock.from_dict(item)
        write_lock(task_lock_path(paths, lock.task_id), lock)
    if paths.events_dir.exists():
        for path in paths.events_dir.glob("*.ndjson"):
            path.unlink()
    for item in _dict_list(raw_v2.get("events")):
        append_event(paths.events_dir, TaskEvent.from_dict(item))


def _clear_v2_state(paths: V2Paths) -> None:
    for directory in paths.tasks_dir.glob("task-*"):
        if directory.is_dir():
            shutil.rmtree(directory)
    for directory in (
        paths.introductions_dir,
        paths.events_dir,
    ):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    if paths.active_task_path.exists():
        paths.active_task_path.unlink()
