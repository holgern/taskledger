from __future__ import annotations

from typing import Literal, cast

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
PlanStatus = Literal["draft", "proposed", "accepted", "superseded", "rejected"]
QuestionStatus = Literal["open", "answered", "dismissed"]
RunStatus = Literal["running", "finished", "passed", "failed", "blocked"]
ValidationResult = Literal["passed", "failed", "blocked"]
ValidationCheckStatus = Literal["pass", "fail", "warn", "not_run"]
FileLinkKind = Literal["code", "test", "doc", "config", "dir", "other", "artifact"]
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


def normalize_task_status_stage(value: str) -> TaskStatusStage:
    if value not in ALLOWED_STAGE_TRANSITIONS:
        raise LaunchError(f"Unsupported task stage: {value}")
    return cast(TaskStatusStage, value)


def normalize_run_type(value: str) -> RunType:
    if value not in {"planning", "implementation", "validation"}:
        raise LaunchError(f"Unsupported run type: {value}")
    return cast(RunType, value)


def normalize_plan_status(value: str) -> PlanStatus:
    if value not in {"draft", "proposed", "accepted", "superseded", "rejected"}:
        raise LaunchError(f"Unsupported plan status: {value}")
    return cast(PlanStatus, value)


def normalize_question_status(value: str) -> QuestionStatus:
    if value not in {"open", "answered", "dismissed"}:
        raise LaunchError(f"Unsupported question status: {value}")
    return cast(QuestionStatus, value)


def normalize_run_status(value: str) -> RunStatus:
    if value not in {"running", "finished", "passed", "failed", "blocked"}:
        raise LaunchError(f"Unsupported run status: {value}")
    return cast(RunStatus, value)


def normalize_validation_result(value: str) -> ValidationResult:
    if value not in {"passed", "failed", "blocked"}:
        raise LaunchError(f"Unsupported validation result: {value}")
    return cast(ValidationResult, value)


def normalize_validation_check_status(value: str) -> ValidationCheckStatus:
    normalized = "not_run" if value == "skip" else value
    if normalized not in {"pass", "fail", "warn", "not_run"}:
        raise LaunchError(f"Unsupported validation check status: {value}")
    return cast(ValidationCheckStatus, normalized)


def normalize_file_link_kind(value: str) -> FileLinkKind:
    normalized = "dir" if value == "directory" else value
    if normalized not in {"code", "test", "doc", "config", "dir", "other", "artifact"}:
        raise LaunchError(f"Unsupported file link kind: {value}")
    return cast(FileLinkKind, normalized)
