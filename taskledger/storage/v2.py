from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from taskledger.domain.models import (
    CodeChangeRecord,
    IntroductionRecord,
    PlanRecord,
    QuestionRecord,
    TaskLock,
    TaskRecord,
    TaskRunRecord,
)
from taskledger.errors import LaunchError
from taskledger.storage import resolve_taskledger_root
from taskledger.storage.atomic import atomic_write_text
from taskledger.storage.frontmatter import (
    normalize_front_matter_newlines,
    read_markdown_front_matter,
    write_markdown_front_matter,
)
from taskledger.storage.locks import read_lock

T = TypeVar("T")


@dataclass(slots=True, frozen=True)
class V2Paths:
    workspace_root: Path
    project_dir: Path
    introductions_dir: Path
    tasks_dir: Path
    plans_dir: Path
    questions_dir: Path
    runs_dir: Path
    changes_dir: Path
    events_dir: Path
    indexes_dir: Path
    tasks_index_path: Path
    active_locks_index_path: Path
    dependencies_index_path: Path
    introductions_index_path: Path


def resolve_v2_paths(workspace_root: Path) -> V2Paths:
    project_dir = resolve_taskledger_root(workspace_root)
    indexes_dir = project_dir / "indexes"
    return V2Paths(
        workspace_root=workspace_root,
        project_dir=project_dir,
        introductions_dir=project_dir / "introductions",
        tasks_dir=project_dir / "tasks",
        plans_dir=project_dir / "plans",
        questions_dir=project_dir / "questions",
        runs_dir=project_dir / "runs",
        changes_dir=project_dir / "changes",
        events_dir=project_dir / "events",
        indexes_dir=indexes_dir,
        tasks_index_path=indexes_dir / "tasks.json",
        active_locks_index_path=indexes_dir / "active_locks.json",
        dependencies_index_path=indexes_dir / "dependencies.json",
        introductions_index_path=indexes_dir / "introductions.json",
    )


def ensure_v2_layout(workspace_root: Path) -> V2Paths:
    paths = resolve_v2_paths(workspace_root)
    for directory in (
        paths.project_dir,
        paths.introductions_dir,
        paths.tasks_dir,
        paths.plans_dir,
        paths.questions_dir,
        paths.runs_dir,
        paths.changes_dir,
        paths.events_dir,
        paths.indexes_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for index_path in (
        paths.tasks_index_path,
        paths.active_locks_index_path,
        paths.dependencies_index_path,
        paths.introductions_index_path,
    ):
        if index_path.exists():
            continue
        atomic_write_text(index_path, "[]\n")
    return paths


def list_tasks(workspace_root: Path) -> list[TaskRecord]:
    paths = ensure_v2_layout(workspace_root)
    return sorted(
        [_load_task(path) for path in paths.tasks_dir.glob("task-*.md")],
        key=lambda item: item.id,
    )


def resolve_task(workspace_root: Path, ref: str) -> TaskRecord:
    normalized_ref = ref.strip().lower()
    for task in list_tasks(workspace_root):
        if task.id == ref or task.slug == normalized_ref:
            return task
    raise LaunchError(f"Task not found: {ref}")


def save_task(workspace_root: Path, task: TaskRecord) -> TaskRecord:
    paths = ensure_v2_layout(workspace_root)
    path = task_markdown_path(paths, task.id)
    if path.stem != task.id:
        raise LaunchError(f"Task id/path mismatch for {task.id}")
    _write_markdown_record(path, task.to_dict(), task.body)
    return task


def list_introductions(workspace_root: Path) -> list[IntroductionRecord]:
    paths = ensure_v2_layout(workspace_root)
    return sorted(
        [_load_intro(path) for path in paths.introductions_dir.glob("intro-*.md")],
        key=lambda item: item.id,
    )


def resolve_introduction(workspace_root: Path, ref: str) -> IntroductionRecord:
    normalized_ref = ref.strip().lower()
    for intro in list_introductions(workspace_root):
        if intro.id == ref or intro.slug == normalized_ref:
            return intro
    raise LaunchError(f"Introduction not found: {ref}")


def save_introduction(
    workspace_root: Path, introduction: IntroductionRecord
) -> IntroductionRecord:
    paths = ensure_v2_layout(workspace_root)
    path = paths.introductions_dir / f"{introduction.id}.md"
    _write_markdown_record(path, introduction.to_dict(), introduction.body)
    return introduction


def list_plans(workspace_root: Path, task_id: str) -> list[PlanRecord]:
    paths = ensure_v2_layout(workspace_root)
    directory = paths.plans_dir / task_id
    return sorted(
        [_load_plan(path) for path in directory.glob("plan-v*.md")],
        key=lambda item: item.plan_version,
    )


def save_plan(workspace_root: Path, plan: PlanRecord) -> PlanRecord:
    paths = ensure_v2_layout(workspace_root)
    path = plan_markdown_path(paths, plan.task_id, plan.plan_version)
    if path.exists():
        raise LaunchError(
            "Plan version already exists: "
            f"{plan.task_id} v{plan.plan_version}"
        )
    _write_markdown_record(path, plan.to_dict(), plan.body)
    return plan


def overwrite_plan(workspace_root: Path, plan: PlanRecord) -> PlanRecord:
    paths = ensure_v2_layout(workspace_root)
    path = plan_markdown_path(paths, plan.task_id, plan.plan_version)
    _write_markdown_record(path, plan.to_dict(), plan.body)
    return plan


def resolve_plan(
    workspace_root: Path,
    task_id: str,
    *,
    version: int | None = None,
) -> PlanRecord:
    plans = list_plans(workspace_root, task_id)
    if not plans:
        raise LaunchError(f"No plans found for task {task_id}")
    if version is None:
        return plans[-1]
    for plan in plans:
        if plan.plan_version == version:
            return plan
    raise LaunchError(f"Plan version not found for task {task_id}: {version}")


def list_questions(workspace_root: Path, task_id: str) -> list[QuestionRecord]:
    paths = ensure_v2_layout(workspace_root)
    directory = paths.questions_dir / task_id
    return sorted(
        [_load_question(path) for path in directory.glob("q-*.md")],
        key=lambda item: item.id,
    )


def resolve_question(
    workspace_root: Path, task_id: str, question_id: str
) -> QuestionRecord:
    for question in list_questions(workspace_root, task_id):
        if question.id == question_id:
            return question
    raise LaunchError(f"Question not found: {question_id}")


def save_question(workspace_root: Path, question: QuestionRecord) -> QuestionRecord:
    paths = ensure_v2_layout(workspace_root)
    path = question_markdown_path(paths, question.task_id, question.id)
    _write_markdown_record(path, question.to_dict(), _render_question_body(question))
    return question


def list_runs(workspace_root: Path, task_id: str) -> list[TaskRunRecord]:
    paths = ensure_v2_layout(workspace_root)
    directory = paths.runs_dir / task_id
    return sorted(
        [_load_run(path) for path in directory.glob("*.md")],
        key=lambda item: item.run_id,
    )


def resolve_run(workspace_root: Path, task_id: str, run_id: str) -> TaskRunRecord:
    for run in list_runs(workspace_root, task_id):
        if run.run_id == run_id:
            return run
    raise LaunchError(f"Run not found: {run_id}")


def save_run(workspace_root: Path, run: TaskRunRecord) -> TaskRunRecord:
    paths = ensure_v2_layout(workspace_root)
    path = run_markdown_path(paths, run.task_id, run.run_id)
    _write_markdown_record(path, run.to_dict(), _render_run_body(run))
    return run


def list_changes(workspace_root: Path, task_id: str) -> list[CodeChangeRecord]:
    paths = ensure_v2_layout(workspace_root)
    directory = paths.changes_dir / task_id
    return sorted(
        [_load_change(path) for path in directory.glob("change-*.md")],
        key=lambda item: item.change_id,
    )


def save_change(
    workspace_root: Path, change: CodeChangeRecord
) -> CodeChangeRecord:
    paths = ensure_v2_layout(workspace_root)
    path = change_markdown_path(paths, change.task_id, change.change_id)
    _write_markdown_record(path, change.to_dict(), change.summary)
    return change


def resolve_change(
    workspace_root: Path, task_id: str, change_id: str
) -> CodeChangeRecord:
    for change in list_changes(workspace_root, task_id):
        if change.change_id == change_id:
            return change
    raise LaunchError(f"Change not found: {change_id}")


def load_active_locks(workspace_root: Path) -> list[TaskLock]:
    paths = ensure_v2_layout(workspace_root)
    locks: list[TaskLock] = []
    for path in sorted(paths.tasks_dir.glob("task-*.lock.yaml")):
        lock = read_lock(path)
        if lock is not None:
            locks.append(lock)
    return locks


def task_markdown_path(paths: V2Paths, task_id: str) -> Path:
    return paths.tasks_dir / f"{task_id}.md"


def task_lock_path(paths: V2Paths, task_id: str) -> Path:
    return paths.tasks_dir / f"{task_id}.lock.yaml"


def plan_markdown_path(paths: V2Paths, task_id: str, version: int) -> Path:
    return paths.plans_dir / task_id / f"plan-v{version}.md"


def question_markdown_path(paths: V2Paths, task_id: str, question_id: str) -> Path:
    return paths.questions_dir / task_id / f"{question_id}.md"


def run_markdown_path(paths: V2Paths, task_id: str, run_id: str) -> Path:
    return paths.runs_dir / task_id / f"{run_id}.md"


def change_markdown_path(paths: V2Paths, task_id: str, change_id: str) -> Path:
    return paths.changes_dir / task_id / f"{change_id}.md"


def _load_task(path: Path) -> TaskRecord:
    return _load_record(path, TaskRecord.from_dict)


def _load_intro(path: Path) -> IntroductionRecord:
    return _load_record(path, IntroductionRecord.from_dict)


def _load_plan(path: Path) -> PlanRecord:
    return _load_record(path, PlanRecord.from_dict)


def _load_question(path: Path) -> QuestionRecord:
    return _load_record(path, QuestionRecord.from_dict)


def _load_run(path: Path) -> TaskRunRecord:
    return _load_record(path, TaskRunRecord.from_dict)


def _load_change(path: Path) -> CodeChangeRecord:
    return _load_record(path, CodeChangeRecord.from_dict)


def _load_record(path: Path, parser: Callable[[dict[str, object]], T]) -> T:
    metadata, body = read_markdown_front_matter(path)
    metadata["body"] = normalize_front_matter_newlines(body).rstrip("\n")
    return parser(metadata)


def _write_markdown_record(path: Path, metadata: dict[str, object], body: str) -> None:
    metadata = dict(metadata)
    metadata.pop("body", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown_front_matter(path, metadata, body.rstrip() + "\n")


def _render_question_body(question: QuestionRecord) -> str:
    lines = ["## Question", "", question.question.strip()]
    lines.extend(["", "## Answer", "", (question.answer or "").strip()])
    return "\n".join(lines).rstrip() + "\n"


def _render_run_body(run: TaskRunRecord) -> str:
    lines: list[str] = ["## Summary", "", (run.summary or "").strip()]
    if run.run_type == "validation":
        lines.extend(["", "## Checks", ""])
        for check in run.checks:
            mark = "x" if check.status == "pass" else " "
            lines.append(f"- [{mark}] {check.name}")
        lines.extend(["", "## Evidence", ""])
        for entry in run.evidence:
            lines.append(f"- {entry}")
        lines.extend(["", "## Recommendation", "", (run.recommendation or "").strip()])
        return "\n".join(lines).rstrip() + "\n"
    lines.extend(["", "## Worklog", ""])
    for entry in run.worklog:
        lines.append(f"- {entry}")
    lines.extend(["", "## Deviations From Plan", ""])
    for entry in run.deviations_from_plan:
        lines.append(f"- {entry}")
    return "\n".join(lines).rstrip() + "\n"
