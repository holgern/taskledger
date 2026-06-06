"""Read-model aggregator for the optional ``taskledger tui`` Textual UI.

The TUI is a presentation adapter. It depends on existing read models:
``serve_read_model``, ``plan_review``, ``task_reports``, and ``code_review``.
The function in this module, :func:`load_tui_snapshot`, returns a single dict
that the TUI consumes. Keeping the aggregator service-owned means the TUI
remains testable without importing Textual and keeps CLI→service boundary
tests honest.

No function in this module imports ``textual``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from taskledger.errors import LaunchError
from taskledger.services.code_review import list_code_review_records
from taskledger.services.plan_review import (
    PlanReviewOptions,
    render_plan_review,
)
from taskledger.services.serve_read_model import (
    ServeReadOptions,
    serve_dashboard_snapshot,
    serve_project_summary,
    serve_task_summaries,
)
from taskledger.services.task_reports import (
    TaskReportOptions,
    render_task_report,
)


def load_tui_snapshot(
    workspace_root: Path,
    *,
    task_ref: str | None = None,
    include_events: bool = False,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Return a dict bundle suitable for rendering the TUI.

    The bundle shape is::

        {
            "kind": "tui_snapshot",
            "project": {...},                # serve_project_summary payload
            "tasks": [...],                  # visible (and optional archived) tasks
            "selected": {...} | None,        # serve_dashboard_snapshot or None
            "plan_review_markdown": str | None,
            "report_markdown": str | None,
            "reviews": [...],                # list_code_review_records dicts
            "include_archived": bool,
        }

    ``selected`` is ``None`` when no task resolves (no ``task_ref`` and no
    active task). The plan review and full task report are loaded only when a
    task is selected. The plan review catch is narrow: only ``LaunchError`` is
    suppressed, so a task without a reviewable plan simply renders an empty
    Plan tab without failing the whole snapshot.
    """

    project = serve_project_summary(workspace_root)
    tasks_payload = serve_task_summaries(workspace_root)
    tasks_raw = tasks_payload.get("tasks")
    tasks: list[dict[str, Any]] = list(tasks_raw) if isinstance(tasks_raw, list) else []

    archived: list[dict[str, Any]] = []
    if include_archived:
        # ``serve_task_summaries`` only returns visible tasks. Pull archived
        # tasks lazily through the storage helper, keeping the optional set
        # out of the default hot path.
        from taskledger.storage.task_store import list_tasks_by_visibility

        for task in list_tasks_by_visibility(workspace_root, visibility="archived"):
            archived.append(
                {
                    "id": task.id,
                    "slug": task.slug,
                    "title": task.title,
                    "status": task.status_stage,
                    "status_stage": task.status_stage,
                    "active_stage": None,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                    "description_summary": task.description_summary,
                    "priority": task.priority,
                    "labels": list(task.labels),
                    "owner": task.owner,
                    "accepted_plan_version": task.accepted_plan_version,
                    "latest_plan_version": task.latest_plan_version,
                    "archived": True,
                }
            )

    selected_ref = task_ref
    if selected_ref is None:
        active = project.get("active_task")
        if isinstance(active, dict):
            selected_ref = str(active.get("task_id") or "") or None

    selected: dict[str, Any] | None = None
    plan_review_markdown: str | None = None
    report_markdown: str | None = None
    reviews: list[dict[str, Any]] = []

    if selected_ref is not None:
        selected_snapshot: dict[str, Any] = serve_dashboard_snapshot(
            workspace_root,
            ref=selected_ref,
            options=ServeReadOptions(include_events=include_events),
        )
        selected = selected_snapshot
        task_raw = selected.get("task")
        task_id = task_raw.get("id") if isinstance(task_raw, dict) else selected_ref
        task_id_str = str(task_id) if task_id is not None else selected_ref

        try:
            plan_review = render_plan_review(
                workspace_root,
                task_id_str,
                options=PlanReviewOptions(),
                format_name="markdown",
            )
        except LaunchError:
            plan_review_markdown = None
        else:
            content = plan_review.get("content")
            if isinstance(content, str):
                plan_review_markdown = content

        report = render_task_report(
            workspace_root,
            task_id_str,
            options=TaskReportOptions(preset="full", include_empty=True),
            format_name="markdown",
        )
        report_content = report.get("content")
        if isinstance(report_content, str):
            report_markdown = report_content

        reviews = [
            record.to_dict()
            for record in list_code_review_records(workspace_root, task_id_str)
        ]

    return {
        "kind": "tui_snapshot",
        "project": project,
        "tasks": tasks,
        "archived_tasks": archived,
        "selected": selected,
        "plan_review_markdown": plan_review_markdown,
        "report_markdown": report_markdown,
        "reviews": reviews,
        "include_archived": include_archived,
    }
