"""Durable sidecar summary index (task_sidecars.json).

Stores aggregate summaries of per-task sidecar collections: todos,
questions, handoffs, reviews, runs, and locks. This is a derived index
rebuilt from canonical records if absent or stale.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from taskledger.domain.models import (
    CodeReviewRecord,
    QuestionRecord,
    TaskHandoffRecord,
    TaskLock,
    TaskRunRecord,
    TaskTodo,
)
from taskledger.storage.common import write_json

if TYPE_CHECKING:
    from taskledger.storage.task_store import V2Paths

logger = logging.getLogger(__name__)

SIDECAR_INDEX_FILENAME = "task_sidecars.json"
SIDECAR_INDEX_SCHEMA_VERSION = 1
_UNSET: object = object()


@dataclass(frozen=True, slots=True)
class TodoSummary:
    total: int = 0
    done: int = 0
    open: int = 0
    first_open_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "done": self.done,
            "open": self.open,
            "first_open_id": self.first_open_id,
        }


@dataclass(frozen=True, slots=True)
class QuestionSummary:
    open: int = 0
    required_open: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "open": self.open,
            "required_open": self.required_open,
        }


@dataclass(frozen=True, slots=True)
class HandoffSummary:
    open: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "open": self.open,
        }


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    latest_implementation_run: str | None = None
    has_review_for_latest_implementation_run: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "latest_implementation_run": (self.latest_implementation_run),
            "has_review_for_latest_implementation_run": (
                self.has_review_for_latest_implementation_run
            ),
        }


@dataclass(frozen=True, slots=True)
class RunSummary:
    running: tuple[str, ...] = ()
    latest_implementation_status: str | None = None
    latest_validation_status: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "running": list(self.running),
            "latest_implementation_status": (self.latest_implementation_status),
            "latest_validation_status": (self.latest_validation_status),
        }


@dataclass(frozen=True, slots=True)
class LockSummary:
    has_lock: bool = False
    stage: str | None = None
    run_id: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "has_lock": self.has_lock,
            "stage": self.stage,
            "run_id": self.run_id,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True, slots=True)
class TaskSidecarSummary:
    task_id: str
    todos: TodoSummary = field(default_factory=TodoSummary)
    questions: QuestionSummary = field(default_factory=QuestionSummary)
    handoffs: HandoffSummary = field(default_factory=HandoffSummary)
    reviews: ReviewSummary = field(default_factory=ReviewSummary)
    runs: RunSummary = field(default_factory=RunSummary)
    locks: LockSummary = field(default_factory=LockSummary)

    def to_dict(self) -> dict[str, object]:
        return {
            "todos": {
                "total": self.todos.total,
                "done": self.todos.done,
                "open": self.todos.open,
                "first_open_id": self.todos.first_open_id,
            },
            "questions": {
                "open": self.questions.open,
                "required_open": self.questions.required_open,
            },
            "handoffs": {
                "open": self.handoffs.open,
            },
            "reviews": {
                "latest_implementation_run": (self.reviews.latest_implementation_run),
                "has_review_for_latest_implementation_run": (
                    self.reviews.has_review_for_latest_implementation_run
                ),
            },
            "runs": {
                "running": list(self.runs.running),
                "latest_implementation_status": (
                    self.runs.latest_implementation_status
                ),
                "latest_validation_status": self.runs.latest_validation_status,
            },
            "locks": {
                "has_lock": self.locks.has_lock,
                "stage": self.locks.stage,
                "run_id": self.locks.run_id,
                "expires_at": self.locks.expires_at,
            },
        }


def _sidecar_index_path(paths: V2Paths) -> Path:
    return paths.indexes_dir / SIDECAR_INDEX_FILENAME


def _compute_todos_summary(todos: list[TaskTodo]) -> TodoSummary:
    total = len(todos)
    done = sum(1 for t in todos if t.done)
    open_count = total - done
    first_open = None
    for t in todos:
        if not t.done:
            first_open = t.id
            break
    return TodoSummary(
        total=total, done=done, open=open_count, first_open_id=first_open
    )


def _compute_questions_summary(questions: list[QuestionRecord]) -> QuestionSummary:
    open_count = sum(1 for q in questions if q.status == "open")
    required_open = sum(
        1 for q in questions if q.status == "open" and q.required_for_plan
    )
    return QuestionSummary(open=open_count, required_open=required_open)


def _compute_handoffs_summary(
    handoffs: list[TaskHandoffRecord],
) -> HandoffSummary:
    return HandoffSummary(open=sum(1 for h in handoffs if h.status == "open"))


def _compute_reviews_summary(
    reviews: list[CodeReviewRecord],
    latest_implementation_run: str | None,
) -> ReviewSummary:
    has_review = any(
        r.implementation_run == latest_implementation_run
        for r in reviews
        if latest_implementation_run is not None
    )
    return ReviewSummary(
        latest_implementation_run=latest_implementation_run,
        has_review_for_latest_implementation_run=has_review,
    )


def _compute_runs_summary(runs: list[TaskRunRecord]) -> RunSummary:
    running = tuple(r.run_id for r in runs if r.status == "running")
    latest_impl = None
    latest_val = None
    for r in reversed(runs):
        if r.run_type == "implementation" and latest_impl is None:
            latest_impl = r.status
        if r.run_type == "validation" and latest_val is None:
            latest_val = r.status
    return RunSummary(
        running=running,
        latest_implementation_status=latest_impl,
        latest_validation_status=latest_val,
    )


def _compute_lock_summary(lock: TaskLock | None) -> LockSummary:
    if lock is None:
        return LockSummary()
    return LockSummary(
        has_lock=True,
        stage=lock.stage,
        run_id=lock.run_id,
        expires_at=lock.expires_at,
    )


def rebuild_sidecar_index(paths: V2Paths) -> dict[str, int]:
    """Rebuild sidecar summaries for all tasks."""
    from taskledger.storage.task_store import (
        list_code_reviews,
        list_handoffs,
        list_questions,
        list_runs,
        list_tasks,
        load_active_locks,
        load_todos,
    )

    tasks = list_tasks(paths.workspace_root)
    lock_by_task: dict[str, TaskLock] = {}
    for lock in load_active_locks(paths.workspace_root):
        lock_by_task[lock.task_id] = lock

    entries: dict[str, dict[str, object]] = {}
    for task in tasks:
        try:
            todos = load_todos(paths.workspace_root, task.id).todos
            questions = list_questions(paths.workspace_root, task.id)
            handoffs = list_handoffs(paths.workspace_root, task.id)
            reviews = list_code_reviews(paths.workspace_root, task.id)
            runs = list_runs(paths.workspace_root, task.id)
            task_lock: TaskLock | None = lock_by_task.get(task.id)

            summary = TaskSidecarSummary(
                task_id=task.id,
                todos=_compute_todos_summary(list(todos)),
                questions=_compute_questions_summary(questions),
                handoffs=_compute_handoffs_summary(handoffs),
                reviews=_compute_reviews_summary(
                    reviews, task.latest_implementation_run
                ),
                runs=_compute_runs_summary(runs),
                locks=_compute_lock_summary(task_lock),
            )
            entries[task.id] = summary.to_dict()
        except Exception:
            logger.warning("Skipping sidecar summary for %s", task.id, exc_info=True)

    from taskledger.timeutils import utc_now_iso

    envelope = {
        "schema_version": SIDECAR_INDEX_SCHEMA_VERSION,
        "object_type": "task_sidecar_index",
        "ledger_ref": paths.ledger_ref,
        "generated_at": utc_now_iso(),
        "entries": entries,
    }
    write_json(_sidecar_index_path(paths), envelope)
    return {"sidecars": len(entries)}


def load_sidecar_index(
    paths: V2Paths,
) -> dict[str, dict[str, object]]:
    """Load sidecar summaries. Rebuilds if missing or malformed."""
    from taskledger.storage.common import try_load_json_object

    path = _sidecar_index_path(paths)
    if not path.exists():
        rebuild_sidecar_index(paths)

    data = try_load_json_object(path, "sidecar index")
    if data is None:
        rebuild_sidecar_index(paths)
        data = try_load_json_object(path, "sidecar index")
    if data is None:
        return {}

    entries = data.get("entries")
    if not isinstance(entries, dict):
        rebuild_sidecar_index(paths)
        data = try_load_json_object(path, "sidecar index") or {}
        entries = data.get("entries", {}) or {}
    assert isinstance(entries, dict)
    return {k: v for k, v in entries.items() if isinstance(v, dict)}


def get_sidecar_summary(paths: V2Paths, task_id: str) -> dict[str, object] | None:
    """Get the sidecar summary for one task."""
    entries = load_sidecar_index(paths)
    return entries.get(task_id)


def update_sidecar_summary(
    paths: V2Paths,
    task_id: str,
    *,
    todos: list[TaskTodo] | None = None,
    questions: list[QuestionRecord] | None = None,
    handoffs: list[TaskHandoffRecord] | None = None,
    reviews: list[CodeReviewRecord] | None = None,
    runs: list[TaskRunRecord] | None = None,
    lock: object = _UNSET,
    latest_implementation_run: str | None = None,
) -> None:
    """Write-through update for one task's sidecar summary.

    Only updates the sections for which data is provided.
    """
    entries = load_sidecar_index(paths)
    current = entries.get(task_id, {})

    if todos is not None:
        current["todos"] = _compute_todos_summary(todos).to_dict()
    if questions is not None:
        current["questions"] = _compute_questions_summary(questions).to_dict()
    if handoffs is not None:
        current["handoffs"] = _compute_handoffs_summary(handoffs).to_dict()
    if reviews is not None:
        current["reviews"] = _compute_reviews_summary(
            reviews, latest_implementation_run
        ).to_dict()
    if runs is not None:
        current["runs"] = _compute_runs_summary(runs).to_dict()
    if lock is not _UNSET:
        current["locks"] = _compute_lock_summary(
            lock if isinstance(lock, (TaskLock, type(None))) else None
        ).to_dict()

    entries[task_id] = current

    from taskledger.storage.common import try_load_json_object

    path = _sidecar_index_path(paths)
    existing = try_load_json_object(path, "sidecar index") or {}

    existing["entries"] = entries
    write_json(path, existing)
