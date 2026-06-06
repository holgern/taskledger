"""Tab content renderers for the taskledger TUI.

This module imports Textual. It must never be imported at process start by
non-TUI code paths. The CLI reaches it only via :func:`taskledger.tui.app.run_tui`.
"""

from __future__ import annotations

from typing import Any

from textual.widgets import Static

# Tab ids used by the TUI; centralised so keybindings and content routing
# agree on the canonical labels.
TAB_SUMMARY = "summary"
TAB_PLAN = "plan"
TAB_TODOS = "todos"
TAB_IMPLEMENTATION = "implementation"
TAB_REVIEWS = "reviews"
TAB_VALIDATION = "validation"
TAB_FILES = "files"
TAB_EVENTS = "events"
TAB_RAW_REPORT = "raw-report"

TAB_ORDER: tuple[str, ...] = (
    TAB_SUMMARY,
    TAB_PLAN,
    TAB_TODOS,
    TAB_IMPLEMENTATION,
    TAB_REVIEWS,
    TAB_VALIDATION,
    TAB_FILES,
    TAB_EVENTS,
    TAB_RAW_REPORT,
)


def default_tab_for_selected(selected: dict[str, Any] | None) -> str:
    """Pick a sensible initial tab for the selected task.

    Mirrors the table in the implementation brief:

    - plan_review → Plan
    - active implementation or implementing → Todos
    - implemented or validating → Validation
    - otherwise → Summary
    """

    if not selected:
        return TAB_SUMMARY
    task = selected.get("task")
    if not isinstance(task, dict):
        return TAB_SUMMARY
    status = str(task.get("status_stage") or "")
    active_stage = task.get("active_stage")
    if status == "plan_review":
        return TAB_PLAN
    if status == "implementing" or active_stage == "implementation":
        return TAB_TODOS
    if status in {"implemented", "validating", "failed_validation"}:
        return TAB_VALIDATION
    return TAB_SUMMARY


def render_summary(selected: dict[str, Any] | None) -> str:
    """Render the Summary tab content for a snapshot's ``selected`` payload."""

    if not selected:
        return "No task selected.\n\nActivate a task or select one from the list."

    task_raw = selected.get("task")
    task: dict[str, Any] = task_raw if isinstance(task_raw, dict) else {}
    na_raw = selected.get("next_action")
    next_action: dict[str, Any] = na_raw if isinstance(na_raw, dict) else {}

    lines: list[str] = []
    title = task.get("title") or ""
    lines.append(f"# {task.get('id', '')} — {title}".rstrip())
    lines.append("")
    lines.append(
        f"status: {task.get('status_stage', '')}    "
        f"active: {task.get('active_stage') or 'none'}"
    )
    slug = task.get("slug")
    if slug:
        lines.append(f"slug: {slug}")
    labels = task.get("labels") or []
    if labels:
        lines.append(f"labels: {', '.join(str(item) for item in labels)}")
    owner = task.get("owner")
    if owner:
        lines.append(f"owner: {owner}")

    next_action_label = next_action.get("action") or "none"
    lines.append("")
    lines.append(f"Next action: {next_action_label}")
    reason = next_action.get("reason")
    if reason:
        lines.append(f"Reason: {reason}")

    primary_command = next_action.get("next_command")
    if primary_command:
        lines.append("")
        lines.append("Primary command:")
        lines.append(f"  $ {primary_command}")

    commands = next_action.get("commands") or []
    if isinstance(commands, list) and commands:
        lines.append("")
        lines.append("Commands:")
        for entry in commands:
            if isinstance(entry, dict):
                cmd = entry.get("command")
                if cmd:
                    lines.append(f"  $ {cmd}")
            elif isinstance(entry, str):
                lines.append(f"  $ {entry}")

    todos = selected.get("todos") or {}
    if isinstance(todos, dict):
        total = todos.get("total", 0)
        done = todos.get("done", 0)
        if total:
            lines.append("")
            lines.append(f"Todos: {done}/{total} done")

    validation = (
        selected.get("validation")
        if isinstance(selected.get("validation"), dict)
        else None
    )
    if validation:
        blockers = validation.get("blockers") or []
        if blockers:
            lines.append("")
            lines.append(f"Validation blockers: {len(blockers)}")
        else:
            lines.append("")
            lines.append("Validation: no blockers")

    return "\n".join(lines).rstrip() + "\n"


def render_plan(
    plan_review_markdown: str | None, selected: dict[str, Any] | None
) -> str:
    """Render the Plan tab.

    Prefers the plan-review markdown when present (it includes approval
    readiness, blockers, lint summary, and approval commands). Falls back to
    a basic plan body summary from the dashboard snapshot.
    """

    if plan_review_markdown:
        return plan_review_markdown.rstrip() + "\n"
    if not selected:
        return "No task selected."
    plan = selected.get("plan") if isinstance(selected.get("plan"), dict) else None
    if not plan:
        return (
            "No reviewable plan yet.\n\n"
            "Plans become reviewable once they are proposed in plan_review stage."
        )
    body = plan.get("body") or plan.get("summary") or ""
    lines = ["# Latest plan", ""]
    if body:
        lines.append(str(body).rstrip())
    else:
        lines.append("Plan body is empty.")
    version = plan.get("version")
    status = plan.get("status")
    if version is not None or status:
        lines.append("")
        lines.append(
            f"version: {version if version is not None else '-'}    "
            f"status: {status or '-'}"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_todos(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "No task selected."
    todos_payload = selected.get("todos")
    if not isinstance(todos_payload, dict):
        return "No todos."
    items = todos_payload.get("items") or []
    if not items:
        return "No todos."
    lines: list[str] = ["# Todos", ""]
    for item in items:
        if not isinstance(item, dict):
            continue
        mark = "x" if item.get("done") else " "
        mandatory = "!" if item.get("mandatory") else " "
        ident = item.get("id", "")
        text = item.get("text", "")
        lines.append(f"[{mark}] {mandatory} {ident} -- {text}".rstrip())
        hint = item.get("validation_hint")
        if hint:
            lines.append(f"    hint: {hint}")
        evidence = item.get("evidence")
        if evidence:
            lines.append(f"    evidence: {evidence}")
    return "\n".join(lines).rstrip() + "\n"


def render_implementation(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "No task selected."
    lines: list[str] = ["# Implementation", ""]

    runs = selected.get("runs") or []
    if isinstance(runs, list) and runs:
        latest = runs[-1]
        if isinstance(latest, dict):
            lines.append(
                f"Latest run: {latest.get('id', '')} "
                f"({latest.get('status', '')}) -- {latest.get('summary', '')}"
            )
            started = latest.get("started_at")
            ended = latest.get("ended_at")
            if started or ended:
                lines.append(f"  started: {started or '-'}    ended: {ended or '-'}")
            lines.append("")

    changes = selected.get("changes") or []
    if isinstance(changes, list) and changes:
        lines.append(f"## Changes ({len(changes)})")
        for change in changes[:50]:
            if isinstance(change, dict):
                lines.append(
                    f"- {change.get('kind', '')}: {change.get('path', '')} "
                    f"-- {change.get('summary', '')}"
                )
        if len(changes) > 50:
            lines.append(f"... ({len(changes) - 50} more changes)")
        lines.append("")

    checks = selected.get("checks") or []
    if isinstance(checks, list) and checks:
        lines.append(f"## Implementation checks ({len(checks)})")
        for check in checks[:50]:
            if isinstance(check, dict):
                exit_code = check.get("exit_code")
                cmd = check.get("command", "") or check.get("summary", "")
                lines.append(f"- exit={exit_code}: {cmd}")
        if len(checks) > 50:
            lines.append(f"... ({len(checks) - 50} more checks)")
        lines.append("")

    if len(lines) <= 2:
        lines.append("No implementation activity yet.")
    return "\n".join(lines).rstrip() + "\n"


def render_reviews(reviews: list[dict[str, Any]]) -> str:
    if not reviews:
        return "No code review records."
    lines: list[str] = [f"# Code reviews ({len(reviews)})", ""]
    for review in reviews:
        ident = review.get("id", "")
        result = review.get("result", "")
        source = review.get("source", "")
        run = review.get("implementation_run_id") or "-"
        worker = review.get("worker_step") or "-"
        lines.append(f"## {ident} -- {result}".rstrip())
        lines.append(f"source: {source}    run: {run}    worker: {worker}".rstrip())
        actor = review.get("actor") or {}
        if isinstance(actor, dict) and actor:
            lines.append(
                f"actor: {actor.get('name', '')} ({actor.get('type', '')})".rstrip()
            )
        summary = review.get("summary")
        if summary:
            lines.append("")
            lines.append(str(summary).rstrip())
        body = review.get("body")
        if body:
            lines.append("")
            lines.append(str(body).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_validation(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "No task selected."
    validation = selected.get("validation")
    if not isinstance(validation, dict):
        return "No validation data."
    lines: list[str] = ["# Validation", ""]

    can_finish = validation.get("can_finish")
    if can_finish is not None:
        lines.append(f"Can finish: {bool(can_finish)}")

    criteria = validation.get("criteria") or []
    if isinstance(criteria, list) and criteria:
        lines.append("")
        lines.append("## Criteria")
        for criterion in criteria:
            if not isinstance(criterion, dict):
                continue
            ident = criterion.get("id", "")
            mandatory = "*" if criterion.get("mandatory") else " "
            status = criterion.get("latest_status") or criterion.get("status") or "-"
            satisfied = criterion.get("satisfied")
            satisfied_label = (
                "yes" if satisfied else "no" if satisfied is False else "-"
            )
            lines.append(
                f"{mandatory} {ident} [{status}] satisfied={satisfied_label}".rstrip()
            )

    blockers = validation.get("blockers") or []
    if isinstance(blockers, list) and blockers:
        lines.append("")
        lines.append(f"## Blockers ({len(blockers)})")
        for blocker in blockers:
            if isinstance(blocker, dict):
                lines.append(
                    f"- {blocker.get('kind', '')}: {blocker.get('message', '')}"
                )
            else:
                lines.append(f"- {blocker}")

    return "\n".join(lines).rstrip() + "\n"


def render_files(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "No task selected."
    files_payload = selected.get("files")
    if not isinstance(files_payload, dict):
        return "No file links."
    links = files_payload.get("links") or []
    if not links:
        return "No file links."
    lines: list[str] = [f"# Files ({len(links)})", ""]
    for link in links:
        if not isinstance(link, dict):
            continue
        lines.append(f"- {link.get('kind', '')}: {link.get('path', '')}".rstrip())
    return "\n".join(lines).rstrip() + "\n"


def render_events(selected: dict[str, Any] | None) -> str:
    if not selected:
        return "No task selected."
    events = selected.get("events")
    if not isinstance(events, dict):
        return "Events not loaded. Press r to refresh after enabling events."
    items = events.get("items") or []
    if not items:
        return "No events."
    lines: list[str] = [f"# Events ({events.get('total', len(items))})", ""]
    for event in items[:50]:
        if isinstance(event, dict):
            lines.append(f"- {event.get('at', '')} {event.get('kind', '')}".rstrip())
    return "\n".join(lines).rstrip() + "\n"


def render_raw_report(report_markdown: str | None) -> str:
    if not report_markdown:
        return "No report available."
    return report_markdown.rstrip() + "\n"


def update_static(widget: Static, content: str) -> None:
    """Helper that wraps ``Static.update`` so callers do not need to import Static."""

    widget.update(content)
