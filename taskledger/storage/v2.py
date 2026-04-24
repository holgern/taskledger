from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import yaml

from taskledger.domain.models import (
    CodeChangeRecord,
    IntroductionRecord,
    LinkCollection,
    PlanRecord,
    QuestionRecord,
    RequirementCollection,
    DependencyRequirement,
    TaskLock,
    TaskRecord,
    TaskRunRecord,
    TodoCollection,
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
    latest_runs_index_path: Path
    plan_versions_index_path: Path


def resolve_v2_paths(workspace_root: Path) -> V2Paths:
    project_dir = resolve_taskledger_root(workspace_root)
    indexes_dir = project_dir / "indexes"
    return V2Paths(
        workspace_root=workspace_root,
        project_dir=project_dir,
        introductions_dir=project_dir / "intros",
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
        latest_runs_index_path=indexes_dir / "latest_runs.json",
        plan_versions_index_path=indexes_dir / "plan_versions.json",
    )


def ensure_v2_layout(workspace_root: Path) -> V2Paths:
    paths = resolve_v2_paths(workspace_root)
    for directory in (
        paths.project_dir,
        paths.introductions_dir,
        paths.tasks_dir,
        paths.events_dir,
        paths.indexes_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for index_path in (
        paths.tasks_index_path,
        paths.active_locks_index_path,
        paths.dependencies_index_path,
        paths.introductions_index_path,
        paths.latest_runs_index_path,
        paths.plan_versions_index_path,
    ):
        if index_path.exists():
            continue
        atomic_write_text(index_path, "[]\n")
    return paths


def list_tasks(workspace_root: Path) -> list[TaskRecord]:
    paths = ensure_v2_layout(workspace_root)
    return sorted(
        [_load_task(path) for path in paths.tasks_dir.glob("task-*/task.md")],
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
    _ensure_task_bundle(paths, task.id)
    path = task_markdown_path(paths, task.id)
    if path.parent.name != task.id:
        raise LaunchError(f"Task id/path mismatch for {task.id}")
    metadata = task.to_dict()
    metadata.pop("todos", None)
    metadata.pop("file_links", None)
    metadata.pop("requirements", None)
    _write_markdown_record(path, metadata, task.body)
    if not task_todos_path(paths, task.id).exists():
        _write_yaml(path=task_todos_path(paths, task.id), payload=_todo_collection(task))
    if not task_links_path(paths, task.id).exists():
        _write_yaml(path=task_links_path(paths, task.id), payload=_link_collection(task))
    if not task_requirements_path(paths, task.id).exists():
        _write_yaml(
            path=task_requirements_path(paths, task.id),
            payload=_requirement_collection(task),
        )
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
    directory = task_plans_dir(paths, task_id)
    return sorted(
        [_load_plan(path) for path in directory.glob("plan-v*.md")],
        key=lambda item: item.plan_version,
    )


def save_plan(workspace_root: Path, plan: PlanRecord) -> PlanRecord:
    paths = ensure_v2_layout(workspace_root)
    path = plan_markdown_path(paths, plan.task_id, plan.plan_version)
    if path.exists():
        raise LaunchError(
            f"Plan version already exists: {plan.task_id} v{plan.plan_version}"
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
    directory = task_questions_dir(paths, task_id)
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
    directory = task_runs_dir(paths, task_id)
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
    directory = task_changes_dir(paths, task_id)
    return sorted(
        [_load_change(path) for path in directory.glob("change-*.md")],
        key=lambda item: item.change_id,
    )


def save_change(workspace_root: Path, change: CodeChangeRecord) -> CodeChangeRecord:
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
    for path in sorted(paths.tasks_dir.glob("task-*/lock.yaml")):
        lock = read_lock(path)
        if lock is not None:
            locks.append(lock)
    return locks


def load_todos(workspace_root: Path, task_id: str) -> TodoCollection:
    paths = ensure_v2_layout(workspace_root)
    path = task_todos_path(paths, task_id)
    if not path.exists():
        return TodoCollection(task_id=task_id)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LaunchError(f"Invalid todo sidecar for {task_id}.")
    return TodoCollection.from_dict(payload)


def save_todos(workspace_root: Path, collection: TodoCollection) -> TodoCollection:
    paths = ensure_v2_layout(workspace_root)
    _ensure_task_bundle(paths, collection.task_id)
    _write_yaml(task_todos_path(paths, collection.task_id), collection.to_dict())
    return collection


def load_links(workspace_root: Path, task_id: str) -> LinkCollection:
    paths = ensure_v2_layout(workspace_root)
    path = task_links_path(paths, task_id)
    if not path.exists():
        return LinkCollection(task_id=task_id)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LaunchError(f"Invalid link sidecar for {task_id}.")
    return LinkCollection.from_dict(payload)


def save_links(workspace_root: Path, collection: LinkCollection) -> LinkCollection:
    paths = ensure_v2_layout(workspace_root)
    _ensure_task_bundle(paths, collection.task_id)
    _write_yaml(task_links_path(paths, collection.task_id), collection.to_dict())
    return collection


def load_requirements(workspace_root: Path, task_id: str) -> RequirementCollection:
    paths = ensure_v2_layout(workspace_root)
    path = task_requirements_path(paths, task_id)
    if not path.exists():
        return RequirementCollection(task_id=task_id)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LaunchError(f"Invalid requirement sidecar for {task_id}.")
    return RequirementCollection.from_dict(payload)


def save_requirements(
    workspace_root: Path, collection: RequirementCollection
) -> RequirementCollection:
    paths = ensure_v2_layout(workspace_root)
    _ensure_task_bundle(paths, collection.task_id)
    _write_yaml(task_requirements_path(paths, collection.task_id), collection.to_dict())
    return collection


def task_dir(paths: V2Paths, task_id: str) -> Path:
    return paths.tasks_dir / task_id


def task_markdown_path(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "task.md"


def task_lock_path(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "lock.yaml"


def task_todos_path(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "todos.yaml"


def task_links_path(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "links.yaml"


def task_requirements_path(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "requirements.yaml"


def task_plans_dir(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "plans"


def task_questions_dir(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "questions"


def task_runs_dir(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "runs"


def task_changes_dir(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "changes"


def task_artifacts_dir(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "artifacts"


def task_audit_dir(paths: V2Paths, task_id: str) -> Path:
    return task_dir(paths, task_id) / "audit"


def plan_markdown_path(paths: V2Paths, task_id: str, version: int) -> Path:
    return task_plans_dir(paths, task_id) / f"plan-v{version:04d}.md"


def question_markdown_path(paths: V2Paths, task_id: str, question_id: str) -> Path:
    return task_questions_dir(paths, task_id) / f"{question_id}.md"


def run_markdown_path(paths: V2Paths, task_id: str, run_id: str) -> Path:
    return task_runs_dir(paths, task_id) / f"{run_id}.md"


def change_markdown_path(paths: V2Paths, task_id: str, change_id: str) -> Path:
    return task_changes_dir(paths, task_id) / f"{change_id}.md"


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


def _ensure_task_bundle(paths: V2Paths, task_id: str) -> None:
    for directory in (
        task_dir(paths, task_id),
        task_plans_dir(paths, task_id),
        task_questions_dir(paths, task_id),
        task_runs_dir(paths, task_id),
        task_changes_dir(paths, task_id),
        task_artifacts_dir(paths, task_id),
        task_audit_dir(paths, task_id),
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _todo_collection(task: TaskRecord) -> dict[str, object]:
    return TodoCollection(task_id=task.id, todos=task.todos).to_dict()


def _link_collection(task: TaskRecord) -> dict[str, object]:
    return LinkCollection(task_id=task.id, links=task.file_links).to_dict()


def _requirement_collection(task: TaskRecord) -> dict[str, object]:
    return RequirementCollection(
        task_id=task.id,
        requirements=tuple(
            DependencyRequirement(task_id=requirement) for requirement in task.requirements
        ),
    ).to_dict()


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, yaml.safe_dump(payload, sort_keys=False))


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
