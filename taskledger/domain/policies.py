from __future__ import annotations

from dataclasses import dataclass

from taskledger.domain.models import TaskLock, TaskRecord, TaskRunRecord
from taskledger.domain.states import (
    EXIT_CODE_APPROVAL_REQUIRED,
    EXIT_CODE_INVALID_TRANSITION,
    EXIT_CODE_LOCK_CONFLICT,
)


@dataclass(frozen=True)
class PolicyDecision:
    ok: bool
    reason: str
    exit_code: int


def metadata_edit_decision(task: TaskRecord, lock: TaskLock | None) -> PolicyDecision:
    if task.status_stage not in {"draft", "plan_review", "approved"}:
        return PolicyDecision(
            False,
            "Task metadata can only be edited in draft, plan_review, or approved.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if lock is not None:
        return PolicyDecision(
            False,
            (
                f"Task {task.id} is locked for {lock.stage}. "
                "Break the lock explicitly before editing metadata."
            ),
            EXIT_CODE_LOCK_CONFLICT,
        )
    return PolicyDecision(True, "Task metadata can be edited.", 0)


def todo_add_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    actor_role: str,
) -> PolicyDecision:
    if task.status_stage not in {"draft", "planning", "plan_review", "approved"}:
        return PolicyDecision(
            False,
            "Todos can only be added before implementation starts.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if task.status_stage == "planning":
        return _active_stage_lock_decision(
            task,
            lock,
            expected_stage="planning",
            action="add todos during planning",
        )
    return PolicyDecision(True, f"{actor_role} can add a todo.", 0)


def todo_toggle_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    actor_role: str,
) -> PolicyDecision:
    if task.status_stage == "implementing":
        return _active_stage_lock_decision(
            task,
            lock,
            expected_stage="implementing",
            action="toggle todos during implementation",
        )
    if task.status_stage in {"validating", "cancelled", "done"}:
        return PolicyDecision(
            False,
            f"Todos cannot be toggled while the task is {task.status_stage}.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if actor_role != "user" and task.status_stage != "implementing":
        return PolicyDecision(
            False,
            "Only the user may toggle todos outside implementation.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return PolicyDecision(True, f"{actor_role} can toggle todos.", 0)


def question_add_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    actor_role: str,
) -> PolicyDecision:
    if task.status_stage not in {"planning", "plan_review"}:
        return PolicyDecision(
            False,
            "Questions can only be added during planning or plan review.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if task.status_stage == "planning" and actor_role != "user":
        return _active_stage_lock_decision(
            task,
            lock,
            expected_stage="planning",
            action="add questions during planning",
        )
    return PolicyDecision(True, f"{actor_role} can add a question.", 0)


def question_mutation_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    actor_role: str,
) -> PolicyDecision:
    if task.status_stage not in {"planning", "plan_review"}:
        return PolicyDecision(
            False,
            "Questions can only be updated during planning or plan review.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if task.status_stage == "planning" and actor_role != "user":
        return _active_stage_lock_decision(
            task,
            lock,
            expected_stage="planning",
            action="update questions during planning",
        )
    return PolicyDecision(True, f"{actor_role} can update the question.", 0)


def plan_propose_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    run: TaskRunRecord | None,
) -> PolicyDecision:
    if task.status_stage != "planning":
        return PolicyDecision(
            False,
            "Plan proposals require the task to be in planning.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if run is None or run.run_type != "planning" or run.status != "running":
        return PolicyDecision(
            False,
            "Plan proposals require an active planning run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _active_stage_lock_decision(
        task,
        lock,
        expected_stage="planning",
        action="propose a plan",
        expected_run_id=run.run_id,
    )


def plan_approve_decision(task: TaskRecord, lock: TaskLock | None) -> PolicyDecision:
    if task.status_stage != "plan_review":
        return PolicyDecision(
            False,
            "Plan approval requires plan_review state.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    if lock is not None:
        return PolicyDecision(
            False,
            (
                f"Task {task.id} still has a {lock.stage} lock. "
                "Break it before plan review actions."
            ),
            EXIT_CODE_LOCK_CONFLICT,
        )
    return PolicyDecision(True, "Plan can be approved.", 0)


def plan_revise_decision(task: TaskRecord, lock: TaskLock | None) -> PolicyDecision:
    if task.status_stage != "plan_review":
        return PolicyDecision(
            False,
            "Plan revision requires plan_review state.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if lock is not None:
        return PolicyDecision(
            False,
            (
                f"Task {task.id} still has a {lock.stage} lock. "
                "Break it before revising the plan."
            ),
            EXIT_CODE_LOCK_CONFLICT,
        )
    return PolicyDecision(True, "Plan can be revised.", 0)


def implementation_mutation_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    run: TaskRunRecord | None,
    action: str,
) -> PolicyDecision:
    if task.status_stage != "implementing":
        return PolicyDecision(
            False,
            f"{action} requires implementing state.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if run is None or run.run_type != "implementation" or run.status != "running":
        return PolicyDecision(
            False,
            f"{action} requires an active implementation run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _active_stage_lock_decision(
        task,
        lock,
        expected_stage="implementing",
        action=action,
        expected_run_id=run.run_id,
    )


def validation_check_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    run: TaskRunRecord | None,
) -> PolicyDecision:
    if task.status_stage != "validating":
        return PolicyDecision(
            False,
            "Validation checks require validating state.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if run is None or run.run_type != "validation" or run.status != "running":
        return PolicyDecision(
            False,
            "Validation checks require an active validation run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _active_stage_lock_decision(
        task,
        lock,
        expected_stage="validating",
        action="record validation checks",
        expected_run_id=run.run_id,
    )


def _active_stage_lock_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    expected_stage: str,
    action: str,
    expected_run_id: str | None = None,
) -> PolicyDecision:
    if lock is None:
        return PolicyDecision(
            False,
            f"Task {task.id} needs an active {expected_stage} lock to {action}.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    if lock.stage != expected_stage:
        return PolicyDecision(
            False,
            f"Task {task.id} is locked for {lock.stage}, not {expected_stage}.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    if expected_run_id is not None and lock.run_id != expected_run_id:
        return PolicyDecision(
            False,
            (
                f"Task {task.id} has a {expected_stage} lock for {lock.run_id}, "
                f"not {expected_run_id}."
            ),
            EXIT_CODE_LOCK_CONFLICT,
        )
    return PolicyDecision(True, f"Task can {action}.", 0)


def require_known_actor_role(actor_role: str) -> str:
    if actor_role not in {"planner", "implementer", "user"}:
        raise ValueError(f"Unsupported actor role: {actor_role}")
    return actor_role
