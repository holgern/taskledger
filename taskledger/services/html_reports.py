from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from jinja2 import Environment, PackageLoader, select_autoescape

from taskledger.errors import LaunchError
from taskledger.services.serve_read_model import (
    serve_project_summary,
    serve_task_summaries,
)
from taskledger.services.task_reports import (
    TaskReportOptions,
    build_task_report_payload,
)
from taskledger.storage.task_store import (
    list_tasks_by_visibility,
    resolve_task_or_active,
)

ReportMode = Literal["static", "served"]


@dataclass(frozen=True)
class HtmlReportOptions:
    preset: str = "full"
    sections: tuple[str, ...] = ()
    include_sections: tuple[str, ...] = ()
    exclude_sections: tuple[str, ...] = ()
    events_limit: int = 50
    command_log_limit: int = 100
    include_command_output: bool = False
    include_empty: bool = True
    refresh_seconds: int | None = None
    mode: ReportMode = "static"
    title_prefix: str = "Taskledger"


@dataclass(frozen=True)
class HtmlSiteOptions:
    include_archived: bool = False
    refresh_seconds: int | None = None
    preset: str = "full"


@lru_cache(maxsize=1)
def _jinja_environment() -> Environment:
    return Environment(
        loader=PackageLoader("taskledger", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _render_template(name: str, context: dict[str, object]) -> str:
    rendered = _jinja_environment().get_template(name).render(**context)
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def render_error_html(
    heading: str,
    message: str,
    *,
    refresh_seconds: int | None = None,
) -> str:
    return _render_template(
        "error.html",
        {
            "title": f"Taskledger — {heading}",
            "page_heading": heading,
            "generated_at": None,
            "refresh_seconds": refresh_seconds,
            "heading": heading,
            "message": message,
        },
    )


def _normalize_refresh_seconds(refresh_seconds: int | None) -> int | None:
    if refresh_seconds is None:
        return None
    if refresh_seconds <= 0:
        raise LaunchError("--refresh-seconds must be greater than 0.")
    return refresh_seconds


def _normalize_record(item: object) -> dict[str, object]:
    to_dict = getattr(item, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, dict):
            return value
    if isinstance(item, dict):
        return item
    return {"value": str(item)}


def _normalize_records(items: object) -> list[dict[str, object]]:
    if not isinstance(items, (list, tuple)):
        return []
    return [_normalize_record(item) for item in items]


def render_task_report_html(
    workspace_root: Path,
    task_ref: str,
    *,
    options: HtmlReportOptions | None = None,
) -> dict[str, object]:
    options = options or HtmlReportOptions()
    refresh_seconds = _normalize_refresh_seconds(options.refresh_seconds)
    resolved_ref = task_ref
    if task_ref.strip().lower() in {"", "active"}:
        resolved_ref = resolve_task_or_active(workspace_root, None).id
    payload = build_task_report_payload(
        workspace_root,
        resolved_ref,
        options=TaskReportOptions(
            preset=options.preset,  # type: ignore[arg-type]
            sections=options.sections,
            include_sections=options.include_sections,
            exclude_sections=options.exclude_sections,
            events_limit=options.events_limit,
            command_log_limit=options.command_log_limit,
            include_command_output=options.include_command_output,
            include_empty=options.include_empty,
        ),
    )
    task = _normalize_record(payload["task"])
    sections_obj = payload.get("sections")
    sections = list(sections_obj) if isinstance(sections_obj, tuple) else []
    loader = payload["_load"]
    assert callable(loader)

    todos = _normalize_records(loader("todos"))
    questions = _normalize_records(loader("questions"))
    runs = _normalize_records(loader("runs"))
    implementation_runs = [
        run for run in runs if run.get("run_type") == "implementation"
    ]
    links = _normalize_records(loader("links"))
    requirements = _normalize_records(loader("requirements"))
    changes = _normalize_records(loader("changes"))
    checks = _normalize_records(loader("checks"))
    command_logs = _normalize_records(loader("command_logs"))
    validation_report = _normalize_record(loader("validation_report"))
    relationships = _normalize_record(loader("relationships"))
    lock = loader("lock")
    lock_record = _normalize_record(lock) if lock is not None else {}
    accepted_plan = payload.get("accepted_plan")
    accepted_plan_record = (
        _normalize_record(accepted_plan) if accepted_plan is not None else None
    )

    acceptance_criteria = (
        _normalize_records(accepted_plan_record.get("criteria"))
        if isinstance(accepted_plan_record, dict)
        else []
    )

    events: list[dict[str, object]] = []
    if "events" in sections:
        all_events = _normalize_records(loader("events"))
        if options.events_limit > 0:
            events = all_events[-options.events_limit :]
        else:
            events = all_events

    next_action_obj = loader("next_action")
    next_action = _normalize_record(next_action_obj) if next_action_obj else None
    validation_status = str(validation_report.get("status", "unknown"))

    generated_at = str(task.get("updated_at") or "")
    title = f"{options.title_prefix} — {task.get('id', 'task')} report"
    html = _render_template(
        "task_report.html",
        {
            "title": title,
            "page_heading": f"Task report: {task.get('id', '')}",
            "generated_at": generated_at,
            "refresh_seconds": refresh_seconds,
            "task": task,
            "active_stage": lock_record.get("stage"),
            "sections": sections,
            "next_action": next_action,
            "relationships": relationships,
            "requirements": requirements,
            "links": links,
            "accepted_plan": accepted_plan_record,
            "acceptance_criteria": acceptance_criteria,
            "todos": todos,
            "todos_total": len(todos),
            "todos_done": sum(1 for todo in todos if bool(todo.get("done"))),
            "questions_total": len(questions),
            "questions_open": sum(
                1 for question in questions if str(question.get("status")) == "open"
            ),
            "implementation_runs": implementation_runs,
            "changes": changes,
            "checks": checks,
            "command_logs": command_logs,
            "validation_report": validation_report,
            "validation_status": validation_status,
            "lock_stage": lock_record.get("stage") or "none",
            "events": events,
        },
    )

    return {
        "kind": "html_task_report",
        "task_id": str(task.get("id", resolved_ref)),
        "title": str(task.get("title", "")),
        "sections": sections,
        "refresh_seconds": refresh_seconds,
        "content": html,
    }


def render_site_index_html(
    workspace_root: Path,
    *,
    options: HtmlSiteOptions | None = None,
) -> dict[str, object]:
    options = options or HtmlSiteOptions()
    refresh_seconds = _normalize_refresh_seconds(options.refresh_seconds)
    project = serve_project_summary(workspace_root)
    if options.include_archived:
        task_records = list_tasks_by_visibility(workspace_root, visibility="all")
        tasks = [
            {
                "id": task.id,
                "slug": task.slug,
                "title": task.title,
                "status_stage": task.status_stage,
                "active_stage": None,
                "archived": task.archived_at is not None,
            }
            for task in task_records
        ]
    else:
        summary = serve_task_summaries(workspace_root)
        tasks_raw = summary.get("tasks")
        tasks = list(tasks_raw) if isinstance(tasks_raw, list) else []
    active_task = project.get("active_task")
    html = _render_template(
        "site_index.html",
        {
            "title": "Taskledger report site",
            "page_heading": "Taskledger HTML reports",
            "generated_at": None,
            "refresh_seconds": refresh_seconds,
            "active_task": active_task if isinstance(active_task, dict) else None,
            "tasks": tasks,
        },
    )
    return {
        "kind": "html_site_index",
        "content": html,
        "task_count": len(tasks),
        "tasks": tasks,
        "active_task": active_task if isinstance(active_task, dict) else None,
        "refresh_seconds": refresh_seconds,
    }


def write_html_site(
    workspace_root: Path,
    output_dir: Path,
    *,
    options: HtmlSiteOptions | None = None,
) -> dict[str, object]:
    options = options or HtmlSiteOptions()
    site = render_site_index_html(workspace_root, options=options)
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.html"
    index_path.write_text(str(site["content"]), encoding="utf-8")

    tasks = site.get("tasks")
    task_entries = list(tasks) if isinstance(tasks, list) else []
    task_paths: list[str] = []
    for task in task_entries:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str):
            continue
        rendered = render_task_report_html(
            workspace_root,
            task_id,
            options=HtmlReportOptions(
                preset=options.preset,
                refresh_seconds=options.refresh_seconds,
                mode="static",
            ),
        )
        task_path = tasks_dir / f"{task_id}.html"
        task_path.write_text(str(rendered["content"]), encoding="utf-8")
        task_paths.append(str(task_path))

    active_task_path: str | None = None
    active_task = site.get("active_task")
    if isinstance(active_task, dict):
        active_task_id = active_task.get("task_id")
        if isinstance(active_task_id, str):
            rendered_active = render_task_report_html(
                workspace_root,
                active_task_id,
                options=HtmlReportOptions(
                    preset=options.preset,
                    refresh_seconds=options.refresh_seconds,
                    mode="static",
                ),
            )
            active_path = output_dir / "active-task.html"
            active_path.write_text(str(rendered_active["content"]), encoding="utf-8")
            active_task_path = str(active_path)

    return {
        "kind": "html_report_site_written",
        "output_dir": str(output_dir),
        "index_path": str(index_path),
        "task_count": len(task_paths),
        "task_paths": task_paths,
        "active_task_path": active_task_path,
    }
