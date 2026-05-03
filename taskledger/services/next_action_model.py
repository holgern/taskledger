"""Pure next-action decision model.

Both CLI navigation and dashboard read model should produce the same
NextActionDecision for the same task state. The frozen dataclass provides
a typed contract for that shared output shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from taskledger.domain.models import (
    TaskLock,
    TaskRecord,
    TaskRunRecord,
)


@dataclass(frozen=True)
class NextActionDecision:
    """Pure decision result for what to do next on a task.

    Attributes:
        action: The recommended action string (e.g. "todo-work",
            "plan-propose", "implement-finish").
        reason: Human-readable reason for the action.
        next_item: Optional structured item that the action targets.
        blockers: Tuple of blocker dicts preventing progress.
        progress: Dict with stage-specific progress counters.
    """

    action: str
    reason: str
    next_item: dict[str, object] | None = None
    blockers: tuple[dict[str, object], ...] = ()
    progress: dict[str, object] = field(default_factory=dict)


def decide_orphaned_active_stage(
    *,
    task: TaskRecord,
    plans: list,
    runs: list[TaskRunRecord],
    lock: TaskLock | None,
    task_next_item: dict[str, object] | None,
) -> tuple[str, str, dict[str, object] | None, list[dict[str, object]]]:
    """Shared orphaned-active-stage decision used by navigation and dashboard."""
    blockers: list[dict[str, object]] = [
        {
            "kind": "active_stage",
            "message": (
                f"Task status is {task.status_stage}, but active_stage is missing."
            ),
        }
    ]
    action = "repair-active-stage"
    reason = f"Task is {task.status_stage}, but no matching active lock/run exists."
    next_item = task_next_item
    if task.status_stage == "implementing":
        latest_run = _find_run(runs, task.latest_implementation_run)
        has_accepted_plan = any(
            plan.plan_version == task.accepted_plan_version
            and plan.status == "accepted"
            for plan in plans
        )
        if (
            latest_run is not None
            and latest_run.run_type == "implementation"
            and latest_run.status == "running"
            and lock is None
            and has_accepted_plan
        ):
            action = "implement-resume"
            reason = "Implementation run is running but the lock is missing."
            blockers.append(
                {
                    "kind": "lock",
                    "message": (
                        "Missing active implementation lock "
                        f"for run {latest_run.run_id}."
                    ),
                }
            )
    return action, reason, next_item, blockers


def _find_run(runs: list[TaskRunRecord], run_id: str | None) -> TaskRunRecord | None:
    if run_id is None:
        return None
    for run in runs:
        if run.run_id == run_id:
            return run
    return None
