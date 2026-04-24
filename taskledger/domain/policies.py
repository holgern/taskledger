from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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


@dataclass(frozen=True)
class PolicyContext:
    task: TaskRecord
    lock: TaskLock | None
    run: TaskRunRecord | None
    active_stage: str | None


def derive_active_stage(
    lock: TaskLock | None,
    runs: Iterable[TaskRunRecord],
) -> str | None:
    if lock is None:
        return None
    for run in runs:
        if (
            run.run_id == lock.run_id
            and run.run_type == lock.run_type
            and run.status == "running"
        ):
            return run.run_type
    return None


def build_policy_context(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    run: TaskRunRecord | None = None,
) -> PolicyContext:
    active_stage = (
        derive_active_stage(lock, (run,)) if run is not None else lock.run_type
    ) if lock is not None else None
    return PolicyContext(task=task, lock=lock, run=run, active_stage=active_stage)


def metadata_edit_decision(task: TaskRecord, lock: TaskLock | None) -> PolicyDecision:
    ctx = build_policy_context(task, lock)
    if ctx.task.status_stage not in {"draft", "plan_review", "approved"}:
        return PolicyDecision(
            False,
            "Task metadata can only be edited in draft, plan_review, or approved.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.active_stage is not None:
        return PolicyDecision(
            False,
            (
                f"Task {ctx.task.id} is locked for {ctx.lock.stage}. "
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
    ctx = build_policy_context(task, lock)
    if ctx.active_stage == "planning":
        return _active_stage_lock_decision(
            ctx,
            expected_stage="planning",
            action="add todos during planning",
        )
    if ctx.active_stage is not None or ctx.task.status_stage not in {
        "draft",
        "plan_review",
        "approved",
    }:
        return PolicyDecision(
            False,
            "Todos can only be added before implementation starts.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return PolicyDecision(True, f"{actor_role} can add a todo.", 0)


def todo_toggle_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    actor_role: str,
) -> PolicyDecision:
    ctx = build_policy_context(task, lock)
    if ctx.active_stage == "implementation":
        return _active_stage_lock_decision(
            ctx,
            expected_stage="implementing",
            action="toggle todos during implementation",
        )
    if ctx.active_stage == "validation" or ctx.task.status_stage in {"cancelled", "done"}:
        return PolicyDecision(
            False,
            f"Todos cannot be toggled while the task is {ctx.task.status_stage}.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if actor_role != "user":
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
    ctx = build_policy_context(task, lock)
    if ctx.active_stage not in {None, "planning"} or ctx.task.status_stage not in {
        "draft",
        "plan_review",
    }:
        return PolicyDecision(
            False,
            "Questions can only be added during planning or plan review.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.active_stage == "planning" and actor_role != "user":
        return _active_stage_lock_decision(
            ctx,
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
    ctx = build_policy_context(task, lock)
    if ctx.active_stage not in {None, "planning"} or ctx.task.status_stage not in {
        "draft",
        "plan_review",
    }:
        return PolicyDecision(
            False,
            "Questions can only be updated during planning or plan review.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.active_stage == "planning" and actor_role != "user":
        return _active_stage_lock_decision(
            ctx,
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
    ctx = build_policy_context(task, lock, run=run)
    if ctx.task.status_stage not in {"draft", "plan_review"} or ctx.active_stage != "planning":
        return PolicyDecision(
            False,
            "Plan proposals require active planning.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.run is None or ctx.run.run_type != "planning" or ctx.run.status != "running":
        return PolicyDecision(
            False,
            "Plan proposals require an active planning run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _active_stage_lock_decision(
        ctx,
        expected_stage="planning",
        action="propose a plan",
        expected_run_id=ctx.run.run_id,
    )


def plan_approve_decision(task: TaskRecord, lock: TaskLock | None) -> PolicyDecision:
    ctx = build_policy_context(task, lock)
    if ctx.task.status_stage != "plan_review":
        return PolicyDecision(
            False,
            "Plan approval requires plan_review state.",
            EXIT_CODE_APPROVAL_REQUIRED,
        )
    if ctx.active_stage is not None:
        return PolicyDecision(
            False,
            (
                f"Task {ctx.task.id} still has a {ctx.lock.stage} lock. "
                "Break it before plan review actions."
            ),
            EXIT_CODE_LOCK_CONFLICT,
        )
    return PolicyDecision(True, "Plan can be approved.", 0)


def plan_revise_decision(task: TaskRecord, lock: TaskLock | None) -> PolicyDecision:
    ctx = build_policy_context(task, lock)
    if ctx.task.status_stage != "plan_review":
        return PolicyDecision(
            False,
            "Plan revision requires plan_review state.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.active_stage is not None:
        return PolicyDecision(
            False,
            (
                f"Task {ctx.task.id} still has a {ctx.lock.stage} lock. "
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
    ctx = build_policy_context(task, lock, run=run)
    if (
        ctx.task.status_stage not in {"approved", "failed_validation"}
        or ctx.active_stage != "implementation"
    ):
        return PolicyDecision(
            False,
            f"{action} requires active implementation.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.run is None or ctx.run.run_type != "implementation" or ctx.run.status != "running":
        return PolicyDecision(
            False,
            f"{action} requires an active implementation run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _active_stage_lock_decision(
        ctx,
        expected_stage="implementing",
        action=action,
        expected_run_id=ctx.run.run_id,
    )


def validation_check_decision(
    task: TaskRecord,
    lock: TaskLock | None,
    *,
    run: TaskRunRecord | None,
) -> PolicyDecision:
    ctx = build_policy_context(task, lock, run=run)
    if ctx.task.status_stage != "implemented" or ctx.active_stage != "validation":
        return PolicyDecision(
            False,
            "Validation checks require active validation.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    if ctx.run is None or ctx.run.run_type != "validation" or ctx.run.status != "running":
        return PolicyDecision(
            False,
            "Validation checks require an active validation run.",
            EXIT_CODE_INVALID_TRANSITION,
        )
    return _active_stage_lock_decision(
        ctx,
        expected_stage="validating",
        action="record validation checks",
        expected_run_id=ctx.run.run_id,
    )


def _active_stage_lock_decision(
    ctx: PolicyContext,
    *,
    expected_stage: str,
    action: str,
    expected_run_id: str | None = None,
) -> PolicyDecision:
    if ctx.lock is None:
        return PolicyDecision(
            False,
            f"Task {ctx.task.id} needs an active {expected_stage} lock to {action}.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    expected_run_type = {
        "planning": "planning",
        "implementing": "implementation",
        "validating": "validation",
    }[expected_stage]
    if ctx.lock.run_type != expected_run_type:
        return PolicyDecision(
            False,
            f"Task {ctx.task.id} is locked for {ctx.lock.stage}, not {expected_stage}.",
            EXIT_CODE_LOCK_CONFLICT,
        )
    if expected_run_id is not None and ctx.lock.run_id != expected_run_id:
        return PolicyDecision(
            False,
            (
                f"Task {ctx.task.id} has a {expected_stage} lock for {ctx.lock.run_id}, "
                f"not {expected_run_id}."
            ),
            EXIT_CODE_LOCK_CONFLICT,
        )
    return PolicyDecision(True, f"Task can {action}.", 0)


def require_known_actor_role(actor_role: str) -> str:
    if actor_role not in {"planner", "implementer", "user"}:
        raise ValueError(f"Unsupported actor role: {actor_role}")
    return actor_role
