from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from taskledger.domain.models import TaskLock, TaskRecord, TaskRunRecord
from taskledger.domain.states import (
    EXIT_CODE_APPROVAL_REQUIRED,
    EXIT_CODE_INVALID_TRANSITION,
    EXIT_CODE_LOCK_CONFLICT,
)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    message: str
    blocking_refs: tuple[str, ...] = ()
    details: dict[str, object] = field(default_factory=dict)
    exit_code: int = 0

    @property
    def ok(self) -> bool:
        return self.allowed

    @property
    def reason(self) -> str:
        return self.message


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


def _modern(decision: PolicyDecision, code: str) -> Decision:
    return Decision(
        allowed=decision.ok,
        code="OK" if decision.ok else code,
        message=decision.reason,
        exit_code=decision.exit_code,
    )


def can_start_planning(task: TaskRecord, ledger: object) -> Decision:
    lock = getattr(ledger, "lock", None)
    allowed = task.status_stage in {"draft", "plan_review"} and lock is None
    return Decision(
        allowed=allowed,
        code="OK" if allowed else "TASK_NOT_PLANNABLE",
        message=(
            "Planning can start."
            if allowed
            else "Planning requires draft or plan_review state without an active lock."
        ),
        exit_code=0 if allowed else EXIT_CODE_INVALID_TRANSITION,
    )


def can_propose_plan(task: TaskRecord, run: TaskRunRecord, ledger: object) -> Decision:
    return _modern(
        plan_propose_decision(task, getattr(ledger, "lock", None), run=run),
        "RUN_LOCK_MISMATCH",
    )


def can_approve_plan(task: TaskRecord, plan: object, ledger: object) -> Decision:
    return _modern(plan_approve_decision(task, getattr(ledger, "lock", None)), "TASK_NOT_IN_REVIEW")


def can_start_implementation(task: TaskRecord, ledger: object) -> Decision:
    lock = getattr(ledger, "lock", None)
    accepted_plan = getattr(ledger, "accepted_plan", None)
    allowed = (
        task.status_stage in {"approved", "failed_validation"}
        and accepted_plan is not None
        and lock is None
    )
    return Decision(
        allowed=allowed,
        code="OK" if allowed else "TASK_NOT_APPROVED",
        message=(
            "Implementation can start."
            if allowed
            else "Implementation requires approved state, an accepted plan, and no active lock."
        ),
        exit_code=0 if allowed else EXIT_CODE_APPROVAL_REQUIRED,
    )


def can_finish_implementation(task: TaskRecord, run: TaskRunRecord, ledger: object) -> Decision:
    return _modern(
        implementation_mutation_decision(
            task,
            getattr(ledger, "lock", None),
            run=run,
            action="finish implementation",
        ),
        "RUN_LOCK_MISMATCH",
    )


def can_start_validation(task: TaskRecord, ledger: object) -> Decision:
    lock = getattr(ledger, "lock", None)
    allowed = task.status_stage == "implemented" and lock is None
    return Decision(
        allowed=allowed,
        code="OK" if allowed else "TASK_NOT_IMPLEMENTED",
        message=(
            "Validation can start."
            if allowed
            else "Validation requires implemented state and no active lock."
        ),
        exit_code=0 if allowed else EXIT_CODE_INVALID_TRANSITION,
    )


def can_finish_validation(task: TaskRecord, run: TaskRunRecord, ledger: object) -> Decision:
    return _modern(
        validation_check_decision(task, getattr(ledger, "lock", None), run=run),
        "RUN_LOCK_MISMATCH",
    )


def can_mark_todo_done(task: TaskRecord, todo: object, actor: object, ledger: object) -> Decision:
    actor_role = getattr(actor, "actor_type", "user")
    return _modern(
        todo_toggle_decision(
            task,
            getattr(ledger, "lock", None),
            actor_role="user" if actor_role == "user" else "implementer",
        ),
        "TODO_NOT_MUTABLE",
    )


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
                f"Task {ctx.task.id} is locked for {ctx.active_stage}. "
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
                f"Task {ctx.task.id} still has a {ctx.active_stage} lock. "
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
                f"Task {ctx.task.id} still has a {ctx.active_stage} lock. "
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
