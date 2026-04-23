from __future__ import annotations

from typing import Literal

from taskledger.errors import LaunchError

TASKLEDGER_V2_FILE_VERSION = "v2"

TaskStatusStage = Literal[
    "draft",
    "planning",
    "plan_review",
    "approved",
    "implementing",
    "implemented",
    "validating",
    "done",
    "failed_validation",
    "cancelled",
]
ActiveTaskStatusStage = Literal["planning", "implementing", "validating"]
RunType = Literal["planning", "implementation", "validation"]
PlanStatus = Literal["proposed", "accepted", "rejected"]
QuestionStatus = Literal["open", "answered", "dismissed"]
RunStatus = Literal["running", "finished"]
ValidationResult = Literal["passed", "failed"]
FileLinkKind = Literal["code", "test", "doc", "config", "directory", "artifact"]
EventName = Literal[
    "task.created",
    "task.updated",
    "task.cancelled",
    "stage.entered",
    "stage.completed",
    "stage.failed",
    "plan.started",
    "plan.proposed",
    "plan.approved",
    "plan.rejected",
    "question.added",
    "question.answered",
    "question.dismissed",
    "implementation.started",
    "implementation.logged",
    "implementation.finished",
    "validation.started",
    "validation.finished",
    "change.logged",
    "todo.added",
    "todo.toggled",
    "lock.acquired",
    "lock.released",
    "lock.broken",
    "doctor.reindexed",
]

ACTIVE_TASK_STAGES = frozenset({"planning", "implementing", "validating"})
IMPLEMENTABLE_TASK_STAGES = frozenset({"approved", "failed_validation"})
CANCELLABLE_TASK_STAGES = frozenset(ACTIVE_TASK_STAGES) | {
    "draft",
    "plan_review",
    "approved",
    "implemented",
    "failed_validation",
}

ALLOWED_STAGE_TRANSITIONS: dict[TaskStatusStage, frozenset[TaskStatusStage]] = {
    "draft": frozenset({"planning", "cancelled"}),
    "planning": frozenset({"plan_review", "cancelled"}),
    "plan_review": frozenset({"planning", "approved", "cancelled"}),
    "approved": frozenset({"implementing", "cancelled"}),
    "implementing": frozenset({"implemented", "cancelled"}),
    "implemented": frozenset({"validating", "cancelled"}),
    "validating": frozenset({"done", "failed_validation", "cancelled"}),
    "failed_validation": frozenset({"approved", "implementing", "cancelled"}),
    "done": frozenset(),
    "cancelled": frozenset(),
}

EXIT_CODE_SUCCESS = 0
EXIT_CODE_BAD_INPUT = 2
EXIT_CODE_MISSING = 3
EXIT_CODE_INVALID_TRANSITION = 4
EXIT_CODE_LOCK_CONFLICT = 5
EXIT_CODE_DEPENDENCY_BLOCKED = 6
EXIT_CODE_DATA_INTEGRITY = 7
EXIT_CODE_APPROVAL_REQUIRED = 8
EXIT_CODE_VALIDATION_FAILED = 9
EXIT_CODE_STORAGE_ERROR = 10


def is_active_stage(stage: TaskStatusStage) -> bool:
    return stage in ACTIVE_TASK_STAGES


def can_transition(current: TaskStatusStage, target: TaskStatusStage) -> bool:
    return target in ALLOWED_STAGE_TRANSITIONS[current]


def require_transition(current: TaskStatusStage, target: TaskStatusStage) -> None:
    if can_transition(current, target):
        return
    raise LaunchError(f"Invalid stage transition: {current} -> {target}")
