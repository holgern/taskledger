from __future__ import annotations

from pathlib import Path

from taskledger.services.tasks import show_task
from taskledger.storage.v2 import (
    list_changes,
    list_plans,
    list_questions,
    list_runs,
    resolve_introduction,
    resolve_plan,
    resolve_task,
)


def render_handoff(
    workspace_root: Path,
    task_ref: str,
    *,
    mode: str,
    format_name: str = "text",
) -> str | dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    payload = show_task(workspace_root, task.id)
    intro = (
        resolve_introduction(workspace_root, task.introduction_ref)
        if task.introduction_ref
        else None
    )
    questions = list_questions(workspace_root, task.id)
    runs = list_runs(workspace_root, task.id)
    changes = list_changes(workspace_root, task.id)
    accepted_plan = _accepted_plan(workspace_root, task.id, task.accepted_plan_version)
    if format_name == "json":
        return _json_handoff(
            mode,
            payload["task"],
            intro=intro.to_dict() if intro is not None else None,
            accepted_plan=accepted_plan.to_dict() if accepted_plan else None,
            questions=[item.to_dict() for item in questions],
            runs=[item.to_dict() for item in runs],
            changes=[item.to_dict() for item in changes],
        )
    return _text_handoff(
        workspace_root,
        task,
        mode=mode,
        intro_body=intro.body.strip() if intro is not None else None,
        questions=questions,
        runs=runs,
        changes=changes,
        accepted_plan_body=accepted_plan.body.strip() if accepted_plan else None,
    )


def _accepted_plan(workspace_root: Path, task_id: str, version: int | None):
    if version is None:
        return None
    return resolve_plan(workspace_root, task_id, version=version)


def _json_handoff(
    mode: str,
    task: object,
    *,
    intro: object,
    accepted_plan: object,
    questions: list[dict[str, object]],
    runs: list[dict[str, object]],
    changes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "kind": "task_handoff",
        "mode": mode,
        "task": task,
        "introduction": intro,
        "accepted_plan": accepted_plan,
        "questions": questions,
        "runs": runs,
        "changes": changes,
    }


def _text_handoff(
    workspace_root: Path,
    task,
    *,
    mode: str,
    intro_body: str | None,
    questions,
    runs,
    changes,
    accepted_plan_body: str | None,
) -> str:
    lines = [f"# {task.title}", "", task.body]
    if intro_body:
        lines.extend(["", "## Introduction", "", intro_body])
    _append_links(lines, task.file_links, task.requirements)
    if mode in {"show", "plan-context"}:
        _append_plan_context(lines, workspace_root, task.id, questions)
    if mode in {"show", "implementation-context"}:
        _append_implementation_context(lines, accepted_plan_body, questions, task.todos)
    if mode in {"show", "validation-context"}:
        _append_validation_context(lines, accepted_plan_body, runs, changes)
    return "\n".join(lines).rstrip() + "\n"


def _append_links(lines: list[str], file_links, requirements) -> None:
    if file_links:
        lines.extend(["", "## Linked Files", ""])
        for link in file_links:
            label = f" ({link.label})" if link.label else ""
            lines.append(f"- `{link.path}` [{link.kind}]{label}")
    if requirements:
        lines.extend(["", "## Dependencies", ""])
        for requirement in requirements:
            lines.append(f"- {requirement}")


def _append_plan_context(
    lines: list[str],
    workspace_root: Path,
    task_id: str,
    questions,
) -> None:
    plans = list_plans(workspace_root, task_id)
    if plans:
        lines.extend(["", "## Plan Versions", ""])
        for plan in plans:
            lines.append(f"- v{plan.plan_version}: {plan.status}")
    open_questions = [question for question in questions if question.status == "open"]
    if open_questions:
        lines.extend(["", "## Open Questions", ""])
        for question in open_questions:
            lines.append(f"- {question.id}: {question.question}")


def _append_implementation_context(
    lines: list[str],
    accepted_plan_body: str | None,
    questions,
    todos,
) -> None:
    if accepted_plan_body is not None:
        lines.extend(["", "## Accepted Plan", "", accepted_plan_body])
    if questions:
        lines.extend(["", "## Question History", ""])
        for question in questions:
            answer = question.answer or "(unanswered)"
            lines.append(f"- {question.question} -> {answer}")
    if todos:
        lines.extend(["", "## Todos", ""])
        for todo in todos:
            mark = "x" if todo.done else " "
            lines.append(f"- [{mark}] {todo.text}")


def _append_validation_context(
    lines: list[str],
    accepted_plan_body: str | None,
    runs,
    changes,
) -> None:
    if accepted_plan_body is not None:
        lines.extend(["", "## Accepted Plan", "", accepted_plan_body])
    impl_runs = [item for item in runs if item.run_type == "implementation"]
    if impl_runs:
        latest_impl = impl_runs[-1]
        lines.extend(["", "## Implementation Summary", "", latest_impl.summary or ""])
    if changes:
        lines.extend(["", "## Code Changes", ""])
        for change in changes:
            lines.append(f"- `{change.path}`: {change.summary}")
