from __future__ import annotations

import re
from pathlib import Path

from taskledger.domain.models import (
    ActorRef,
    CodeChangeRecord,
    PlanRecord,
    ReleaseRecord,
    TaskEvent,
    TaskRecord,
    TaskRunRecord,
)
from taskledger.errors import LaunchError
from taskledger.services.actors import resolve_actor, resolve_harness
from taskledger.storage.events import append_event, next_event_id
from taskledger.storage.indexes import rebuild_v2_indexes
from taskledger.storage.task_store import (
    list_changes,
    list_plans,
    list_releases,
    list_runs,
    list_tasks,
    load_todos,
    resolve_release,
    resolve_task,
    resolve_v2_paths,
    save_release,
)
from taskledger.timeutils import utc_now_iso


def tag_release(
    workspace_root: Path,
    *,
    version: str,
    at_task: str,
    note: str | None = None,
    changelog_file: str | None = None,
    previous_version: str | None = None,
    actor: ActorRef | None = None,
) -> dict[str, object]:
    boundary_task = resolve_task(workspace_root, at_task)
    if boundary_task.status_stage != "done":
        raise LaunchError(
            f"Release boundaries must point to done tasks: {boundary_task.id} is "
            f"{boundary_task.status_stage}."
        )
    existing = list_releases(workspace_root)
    if any(item.version == version for item in existing):
        raise LaunchError(f"Release version already exists: {version}")

    boundary_number = _task_number(boundary_task.id)
    previous = _resolve_previous_release(
        existing,
        boundary_number,
        explicit=previous_version,
    )
    release_actor = actor or resolve_actor(workspace_root=workspace_root)
    task_count = _count_done_tasks_between(
        workspace_root,
        lower_task_id=previous.boundary_task_id if previous is not None else None,
        upper_task_id=boundary_task.id,
    )
    release = ReleaseRecord(
        version=version,
        boundary_task_id=boundary_task.id,
        created_by=release_actor,
        note=note,
        changelog_file=changelog_file,
        task_count=task_count if previous is not None else None,
        previous_version=previous.version if previous is not None else None,
    )
    save_release(workspace_root, release)
    event_id = _append_release_event(
        workspace_root,
        task_id=boundary_task.id,
        event_name="release.tagged",
        data={
            "version": release.version,
            "boundary_task_id": release.boundary_task_id,
            "note": release.note,
            "previous_version": release.previous_version,
        },
    )
    rebuild_v2_indexes(resolve_v2_paths(workspace_root))
    paths = resolve_v2_paths(workspace_root)
    return {
        "kind": "release",
        "ledger_ref": paths.ledger_ref,
        "release": release.to_dict(),
        "boundary_task": _task_summary(boundary_task),
        "events": [event_id],
    }


def list_release_records(workspace_root: Path) -> list[dict[str, object]]:
    return [item.to_dict() for item in list_releases(workspace_root)]


def show_release(workspace_root: Path, version: str) -> dict[str, object]:
    release = resolve_release(workspace_root, version)
    boundary_task = resolve_task(workspace_root, release.boundary_task_id)
    paths = resolve_v2_paths(workspace_root)
    return {
        "kind": "release",
        "ledger_ref": paths.ledger_ref,
        "release": release.to_dict(),
        "boundary_task": _task_summary(boundary_task),
    }


def build_changelog_context(
    workspace_root: Path,
    *,
    version: str,
    since_version: str | None = None,
    since_task: str | None = None,
    until_task: str | None = None,
    format_name: str = "markdown",
) -> str | dict[str, object]:
    if bool(since_version) == bool(since_task):
        raise LaunchError("Provide exactly one of --since or --since-task.")

    lower_boundary, resolved_since_version = _resolve_lower_boundary(
        workspace_root,
        since_version=since_version,
        since_task=since_task,
    )
    upper_boundary = _resolve_upper_boundary(
        workspace_root,
        lower_boundary_task_id=lower_boundary.id,
        until_task=until_task,
    )
    included, omitted = _collect_range_tasks(
        workspace_root,
        lower_boundary_task_id=lower_boundary.id,
        upper_boundary_task_id=upper_boundary.id,
    )
    payload: dict[str, object] = {
        "kind": "release_changelog_context",
        "version": version,
        "ledger_ref": resolve_v2_paths(workspace_root).ledger_ref,
        "since_version": resolved_since_version,
        "since_task_id": lower_boundary.id,
        "until_task_id": upper_boundary.id,
        "task_count": len(included),
        "omitted_task_count": len(omitted),
        "tasks": included,
        "omitted_tasks": omitted,
    }
    if format_name == "json":
        return payload
    if format_name != "markdown":
        raise LaunchError(f"Unsupported release changelog format: {format_name}")
    return _render_markdown(payload)


def _resolve_previous_release(
    releases: list[ReleaseRecord],
    boundary_number: int,
    *,
    explicit: str | None,
) -> ReleaseRecord | None:
    if explicit is not None:
        for release in releases:
            if release.version != explicit:
                continue
            if _task_number(release.boundary_task_id) >= boundary_number:
                raise LaunchError(
                    f"Previous release {explicit} must be before the new boundary task."
                )
            return release
        raise LaunchError(f"Release not found: {explicit}")
    candidates = [
        release
        for release in releases
        if _task_number(release.boundary_task_id) < boundary_number
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: _task_number(item.boundary_task_id))


def _resolve_lower_boundary(
    workspace_root: Path,
    *,
    since_version: str | None,
    since_task: str | None,
) -> tuple[TaskRecord, str | None]:
    if since_version is not None:
        release = resolve_release(workspace_root, since_version)
        task = resolve_task(workspace_root, release.boundary_task_id)
        return task, release.version
    assert since_task is not None
    task = resolve_task(workspace_root, since_task)
    if task.status_stage != "done":
        raise LaunchError(
            f"Bootstrap release boundary must point to a done task: {task.id} is "
            f"{task.status_stage}."
        )
    return task, None


def _resolve_upper_boundary(
    workspace_root: Path,
    *,
    lower_boundary_task_id: str,
    until_task: str | None,
) -> TaskRecord:
    lower_number = _task_number(lower_boundary_task_id)
    if until_task is not None:
        task = resolve_task(workspace_root, until_task)
        upper_number = _task_number(task.id)
        if upper_number <= lower_number:
            raise LaunchError("Upper boundary task must be after the lower boundary.")
        return task

    done_candidates = [
        task
        for task in list_tasks(workspace_root)
        if task.status_stage == "done" and _task_number(task.id) > lower_number
    ]
    if not done_candidates:
        return resolve_task(workspace_root, lower_boundary_task_id)
    return max(done_candidates, key=lambda item: _task_number(item.id))


def _collect_range_tasks(
    workspace_root: Path,
    *,
    lower_boundary_task_id: str,
    upper_boundary_task_id: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    lower_number = _task_number(lower_boundary_task_id)
    upper_number = _task_number(upper_boundary_task_id)
    in_range = [
        task
        for task in list_tasks(workspace_root)
        if lower_number < _task_number(task.id) <= upper_number
    ]
    included = [
        _task_context_payload(workspace_root, task)
        for task in in_range
        if task.status_stage == "done"
    ]
    omitted: list[dict[str, object]] = [
        {
            "task_id": task.id,
            "slug": task.slug,
            "title": task.title,
            "status_stage": task.status_stage,
            "reason": f"omitted because status is `{task.status_stage}`",
        }
        for task in in_range
        if task.status_stage != "done"
    ]
    return included, omitted


def _task_context_payload(workspace_root: Path, task: TaskRecord) -> dict[str, object]:
    plans = list_plans(workspace_root, task.id)
    accepted_plan = _accepted_plan(task, plans)
    implementation_run = _latest_run_by_id(
        list_runs(workspace_root, task.id), task.latest_implementation_run
    )
    validation_run = _latest_run_by_id(
        list_runs(workspace_root, task.id), task.latest_validation_run
    )
    all_changes = list_changes(workspace_root, task.id)
    relevant_changes = _changes_for_run(
        all_changes,
        implementation_run.run_id if implementation_run else None,
    )
    validation_evidence = _validation_evidence(validation_run)
    task_todos = load_todos(workspace_root, task.id).todos
    summary = _task_summary_text(task, accepted_plan, implementation_run)
    implementation_summary = None
    if implementation_run is not None:
        implementation_summary = implementation_run.summary or _first_text(
            implementation_run.worklog
        )
    validation_summary = None
    validation_result = None
    validation_run_id = None
    if validation_run is not None:
        validation_summary = validation_run.summary or _first_text(
            validation_run.worklog
        )
        validation_result = validation_run.result
        validation_run_id = validation_run.run_id
    return {
        "task_id": task.id,
        "slug": task.slug,
        "title": task.title,
        "status_stage": task.status_stage,
        "task_type": task.task_type,
        "labels": list(task.labels),
        "summary": summary,
        "accepted_plan_version": task.accepted_plan_version,
        "implementation": {
            "run_id": implementation_run.run_id if implementation_run else None,
            "summary": implementation_summary,
            "changes": [
                {
                    "change_id": change.change_id,
                    "kind": change.kind,
                    "path": change.path,
                    "summary": change.summary,
                }
                for change in relevant_changes
            ],
        },
        "validation": {
            "run_id": validation_run_id,
            "result": validation_result,
            "summary": validation_summary,
            "evidence": validation_evidence,
        },
        "todo_count": len(task_todos),
    }


def _accepted_plan(task: TaskRecord, plans: list[PlanRecord]) -> PlanRecord | None:
    if task.accepted_plan_version is not None:
        for plan in plans:
            if plan.plan_version == task.accepted_plan_version:
                return plan
    return plans[-1] if plans else None


def _latest_run_by_id(
    runs: list[TaskRunRecord], run_id: str | None
) -> TaskRunRecord | None:
    if run_id is not None:
        for run in runs:
            if run.run_id == run_id:
                return run
    return runs[-1] if runs else None


def _changes_for_run(
    changes: list[CodeChangeRecord], run_id: str | None
) -> list[CodeChangeRecord]:
    if run_id is None:
        return changes
    matching = [change for change in changes if change.implementation_run == run_id]
    return matching or changes


def _validation_evidence(validation_run: TaskRunRecord | None) -> list[str]:
    if validation_run is None:
        return []
    evidence: list[str] = []
    for entry in validation_run.evidence:
        if entry not in evidence:
            evidence.append(entry)
    for check in validation_run.checks:
        for entry in check.evidence:
            if entry not in evidence:
                evidence.append(entry)
    return evidence


def _task_summary_text(
    task: TaskRecord,
    accepted_plan: PlanRecord | None,
    implementation_run: TaskRunRecord | None,
) -> str | None:
    if task.description_summary:
        return task.description_summary
    if accepted_plan is not None and accepted_plan.goal:
        return accepted_plan.goal
    if implementation_run is not None and implementation_run.summary:
        return implementation_run.summary
    return _summary_line(task.body)


def _render_markdown(payload: dict[str, object]) -> str:
    version = str(payload["version"])
    since_version = payload.get("since_version")
    since_task_id = str(payload["since_task_id"])
    until_task_id = str(payload["until_task_id"])
    lines = [
        f"# Changelog source for taskledger {version}",
        "",
        "## LLM instruction",
        "",
        f"Write a concise human changelog for taskledger version {version}.",
        "Use only the taskledger data below. Do not invent changes.",
        (
            "Group entries under headings such as Added, Changed, Fixed, "
            "Documentation, and Internal when useful."
        ),
        (
            "Mention user-visible CLI/API/storage changes. Avoid internal "
            "task IDs in the final changelog unless useful."
        ),
        "",
        "## Release range",
        "",
        f"- Version being prepared: {version}",
    ]
    if since_version is not None:
        lines.append(f"- Previous release: {since_version}")
    else:
        lines.append("- Previous release: bootstrap via --since-task")
    lines.extend(
        [
            f"- Previous release boundary: {since_task_id}",
            f"- Included through: {until_task_id}",
            f"- Included done tasks: {payload['task_count']}",
            f"- Omitted tasks in range: {payload['omitted_task_count']}",
            "",
            "## Candidate changes",
            "",
        ]
    )
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        lines.append("(none)")
    else:
        for task in tasks:
            if not isinstance(task, dict):
                continue
            lines.extend(_render_markdown_task(task))
    omitted = payload.get("omitted_tasks")
    if isinstance(omitted, list) and omitted:
        lines.extend(["", "## Omitted tasks", ""])
        for task in omitted:
            if not isinstance(task, dict):
                continue
            lines.append(
                f"- {task['task_id']}: {task['title']} — omitted because "
                f"status is `{task['status_stage']}`."
            )
    return "\n".join(lines).rstrip() + "\n"


def _render_markdown_task(task: dict[str, object]) -> list[str]:
    lines = [f"### {task['task_id']} — {task['title']}", ""]
    lines.append(f"- Status: {task['status_stage']}")
    task_type = task.get("task_type")
    if isinstance(task_type, str) and task_type == "recorded":
        lines.append(f"- Type: {task_type}")
    labels = task.get("labels")
    if isinstance(labels, list) and labels:
        lines.append("- Labels: " + ", ".join(str(item) for item in labels))
    summary = task.get("summary")
    if isinstance(summary, str) and summary.strip():
        lines.append(f"- Summary: {summary}")
    accepted_plan_version = task.get("accepted_plan_version")
    if isinstance(accepted_plan_version, int):
        lines.append(f"- Accepted plan: plan-v{accepted_plan_version}")
    implementation = task.get("implementation")
    if isinstance(implementation, dict):
        impl_summary = implementation.get("summary")
        if isinstance(impl_summary, str) and impl_summary.strip():
            lines.append(f"- Implementation summary: {impl_summary}")
    validation = task.get("validation")
    if isinstance(validation, dict):
        result = validation.get("result")
        summary_text = validation.get("summary")
        if isinstance(result, str):
            if isinstance(summary_text, str) and summary_text.strip():
                lines.append(f"- Validation summary/result: {result} — {summary_text}")
            else:
                lines.append(f"- Validation summary/result: {result}")
    if isinstance(implementation, dict):
        changes = implementation.get("changes")
        if isinstance(changes, list) and changes:
            lines.extend(["- Relevant changes:"])
            for change in changes:
                if not isinstance(change, dict):
                    continue
                lines.append(
                    f"  - {change['kind']} `{change['path']}`: {change['summary']}"
                )
    if isinstance(validation, dict):
        evidence = validation.get("evidence")
        if isinstance(evidence, list) and evidence:
            lines.extend(["- Evidence:"])
            for entry in evidence:
                lines.append(f"  - {entry}")
    lines.append("")
    return lines


def _append_release_event(
    workspace_root: Path,
    *,
    task_id: str,
    event_name: str,
    data: dict[str, object],
) -> str:
    paths = resolve_v2_paths(workspace_root)
    timestamp = utc_now_iso()
    event_id = next_event_id(paths.events_dir, timestamp)
    append_event(
        paths.events_dir,
        TaskEvent(
            ts=timestamp,
            event=event_name,
            task_id=task_id,
            actor=resolve_actor(workspace_root=workspace_root),
            harness=resolve_harness(
                workspace_root=workspace_root,
                cwd=workspace_root,
            ),
            event_id=event_id,
            data=data,
        ),
    )
    return event_id


def _task_summary(task: TaskRecord) -> dict[str, object]:
    return {
        "task_id": task.id,
        "slug": task.slug,
        "title": task.title,
        "status_stage": task.status_stage,
    }


def _count_done_tasks_between(
    workspace_root: Path,
    *,
    lower_task_id: str | None,
    upper_task_id: str,
) -> int:
    lower_number = _task_number(lower_task_id) if lower_task_id is not None else 0
    upper_number = _task_number(upper_task_id)
    return sum(
        1
        for task in list_tasks(workspace_root)
        if task.status_stage == "done"
        and lower_number < _task_number(task.id) <= upper_number
    )


def _task_number(task_id: str) -> int:
    match = re.fullmatch(r"task-(\d+)", task_id)
    if match is None:
        raise LaunchError(f"Release ranges require numeric task ids: {task_id}")
    return int(match.group(1))


def _summary_line(text: str | None) -> str | None:
    if text is None:
        return None
    stripped = " ".join(text.split())
    return stripped[:117] + "..." if len(stripped) > 120 else stripped


def _first_text(values: tuple[str, ...]) -> str | None:
    for value in values:
        if value.strip():
            return value
    return None


__all__ = [
    "build_changelog_context",
    "list_release_records",
    "show_release",
    "tag_release",
]
