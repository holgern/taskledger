"""Tests for taskledger.domain.policies covering uncovered branches."""

from __future__ import annotations

from dataclasses import dataclass

from taskledger.domain.models import ActorRef, TaskLock, TaskRecord, TaskRunRecord
from taskledger.domain.policies import (
    Decision,
    build_policy_context,
    can_approve_plan,
    can_finish_implementation,
    can_finish_validation,
    can_mark_todo_done,
    can_propose_plan,
    can_start_implementation,
    can_start_planning,
    can_start_validation,
    derive_active_stage,
    implementation_mutation_decision,
    metadata_edit_decision,
    plan_approve_decision,
    plan_propose_decision,
    plan_revise_decision,
    question_add_decision,
    question_mutation_decision,
    require_known_actor_role,
    todo_add_decision,
    todo_toggle_decision,
    validation_check_decision,
)


def _actor() -> ActorRef:
    return ActorRef(actor_type="agent", actor_name="taskledger")


def _task(**overrides) -> TaskRecord:
    defaults = dict(
        id="task-0001",
        slug="task-0001",
        title="Task",
        body="desc",
        status_stage="draft",
    )
    defaults.update(overrides)
    return TaskRecord(**defaults)


def _lock(**overrides) -> TaskLock:
    defaults = dict(
        lock_id="lock-1",
        task_id="task-0001",
        stage="planning",
        run_id="run-0001",
        created_at="2026-04-24T08:00:00+00:00",
        expires_at=None,
        reason="test",
        holder=_actor(),
    )
    defaults.update(overrides)
    return TaskLock(**defaults)


def _run(**overrides) -> TaskRunRecord:
    defaults = dict(
        run_id="run-0001",
        task_id="task-0001",
        run_type="planning",
        status="running",
    )
    defaults.update(overrides)
    return TaskRunRecord(**defaults)


@dataclass
class FakeLedger:
    lock: TaskLock | None = None
    accepted_plan: object | None = None


@dataclass
class FakeActor:
    actor_type: str = "user"


# -- derive_active_stage --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-active-stage-requires-matching-running-run
def test_derive_active_stage_lock_no_runs() -> None:
    lock = _lock()
    assert derive_active_stage(lock, []) is None


def test_derive_active_stage_matching_run() -> None:
    lock = _lock(run_id="run-0001", stage="planning")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    assert derive_active_stage(lock, [run]) == "planning"


def test_derive_active_stage_run_not_running() -> None:
    lock = _lock(run_id="run-0001", stage="planning")
    run = _run(run_id="run-0001", run_type="planning", status="finished")
    assert derive_active_stage(lock, [run]) is None


def test_derive_active_stage_run_id_mismatch() -> None:
    lock = _lock(run_id="run-0001", stage="planning")
    run = _run(run_id="run-9999", run_type="planning", status="running")
    assert derive_active_stage(lock, [run]) is None


def test_derive_active_stage_run_type_mismatch() -> None:
    lock = _lock(run_id="run-0001", stage="implementing")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    assert derive_active_stage(lock, [run]) is None


# -- build_policy_context --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-build-policy-context-no-lock-no-run
def test_build_policy_context_no_lock_no_run() -> None:
    task = _task()
    ctx = build_policy_context(task, None)
    assert ctx.active_stage is None
    assert ctx.lock is None
    assert ctx.run is None


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-build-policy-context-with-lock-and-run
def test_build_policy_context_with_lock_and_run() -> None:
    task = _task()
    lock = _lock(stage="planning", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    ctx = build_policy_context(task, lock, run=run)
    assert ctx.active_stage == "planning"


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-build-policy-context-lock-without-run
def test_build_policy_context_lock_without_run() -> None:
    task = _task()
    lock = _lock(stage="implementing", run_id="run-0001")
    ctx = build_policy_context(task, lock)
    assert ctx.active_stage == "implementation"


# -- can_start_planning --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-planning-can-start-from-plannable-stages
def test_can_start_planning_draft_no_lock() -> None:
    task = _task(status_stage="draft")
    assert can_start_planning(task, FakeLedger()).ok is True


def test_can_start_planning_plan_review_no_lock() -> None:
    task = _task(status_stage="plan_review")
    assert can_start_planning(task, FakeLedger()).ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-planning-rejected-if-locked
def test_can_start_planning_rejected_if_locked() -> None:
    task = _task(status_stage="draft")
    lock = _lock()
    decision = can_start_planning(task, FakeLedger(lock=lock))
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-planning-rejected-if-wrong-stage
def test_can_start_planning_rejected_if_wrong_stage() -> None:
    task = _task(status_stage="approved")
    decision = can_start_planning(task, FakeLedger())
    assert decision.ok is False


# -- can_propose_plan --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-propose-plan-ok
def test_can_propose_plan_ok() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    decision = can_propose_plan(task, run, FakeLedger(lock=lock))
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-propose-plan-denied-wrong-stage
def test_can_propose_plan_denied_wrong_stage() -> None:
    task = _task(status_stage="approved")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    decision = can_propose_plan(task, run, FakeLedger())
    assert decision.ok is False


# -- can_approve_plan --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-approve-plan-ok
def test_can_approve_plan_ok() -> None:
    task = _task(status_stage="plan_review")
    decision = can_approve_plan(task, object(), FakeLedger())
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-approve-plan-denied-wrong-stage
def test_can_approve_plan_denied_wrong_stage() -> None:
    task = _task(status_stage="draft")
    decision = can_approve_plan(task, object(), FakeLedger())
    assert decision.ok is False


# -- can_start_implementation --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-implementation-ok
def test_can_start_implementation_ok() -> None:
    task = _task(status_stage="approved")
    decision = can_start_implementation(task, FakeLedger(accepted_plan=object()))
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-implementation-failed-validation-ok
def test_can_start_implementation_failed_validation_ok() -> None:
    task = _task(status_stage="failed_validation")
    decision = can_start_implementation(task, FakeLedger(accepted_plan=object()))
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-implementation-no-accepted-plan
def test_can_start_implementation_no_accepted_plan() -> None:
    task = _task(status_stage="approved")
    decision = can_start_implementation(task, FakeLedger())
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-implementation-locked
def test_can_start_implementation_locked() -> None:
    task = _task(status_stage="approved")
    lock = _lock()
    decision = can_start_implementation(
        task, FakeLedger(accepted_plan=object(), lock=lock)
    )
    assert decision.ok is False


# -- can_finish_implementation --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-finish-implementation-ok
def test_can_finish_implementation_ok() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="implementing", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="implementation", status="running")
    decision = can_finish_implementation(task, run, FakeLedger(lock=lock))
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-finish-implementation-wrong-stage
def test_can_finish_implementation_wrong_stage() -> None:
    task = _task(status_stage="draft")
    run = _run()
    decision = can_finish_implementation(task, run, FakeLedger())
    assert decision.ok is False


# -- can_start_validation --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-validation-ok
def test_can_start_validation_ok() -> None:
    task = _task(status_stage="implemented")
    decision = can_start_validation(task, FakeLedger())
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-validation-wrong-stage
def test_can_start_validation_wrong_stage() -> None:
    task = _task(status_stage="draft")
    decision = can_start_validation(task, FakeLedger())
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-start-validation-locked
def test_can_start_validation_locked() -> None:
    task = _task(status_stage="implemented")
    lock = _lock()
    decision = can_start_validation(task, FakeLedger(lock=lock))
    assert decision.ok is False


# -- can_finish_validation --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-finish-validation-ok
def test_can_finish_validation_ok() -> None:
    task = _task(status_stage="implemented")
    lock = _lock(stage="validating", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="validation", status="running")
    decision = can_finish_validation(task, run, FakeLedger(lock=lock))
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-finish-validation-denied
def test_can_finish_validation_denied() -> None:
    task = _task(status_stage="draft")
    run = _run()
    decision = can_finish_validation(task, run, FakeLedger())
    assert decision.ok is False


# -- can_mark_todo_done --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-mark-todo-done-user
def test_can_mark_todo_done_user() -> None:
    task = _task(status_stage="draft")
    actor = FakeActor(actor_type="user")
    decision = can_mark_todo_done(task, object(), actor, FakeLedger())
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-can-mark-todo-done-agent-denied
def test_can_mark_todo_done_agent_denied() -> None:
    task = _task(status_stage="draft")
    actor = FakeActor(actor_type="agent")
    decision = can_mark_todo_done(task, object(), actor, FakeLedger())
    assert decision.ok is False


# -- metadata_edit_decision --


def test_metadata_edit_decision_ok() -> None:
    task = _task(status_stage="draft")
    assert metadata_edit_decision(task, None).ok is True


def test_metadata_edit_decision_approved() -> None:
    task = _task(status_stage="approved")
    assert metadata_edit_decision(task, None).ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-metadata-edit-decision-wrong-stage
def test_metadata_edit_decision_wrong_stage() -> None:
    task = _task(status_stage="implemented")
    decision = metadata_edit_decision(task, None)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-metadata-edit-decision-locked
def test_metadata_edit_decision_locked() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    _run(run_id="run-0001", run_type="planning", status="running")
    decision = metadata_edit_decision(task, lock)
    assert decision.ok is False


# -- todo_add_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-add-decision-ok
def test_todo_add_decision_ok() -> None:
    task = _task(status_stage="draft")
    decision = todo_add_decision(task, None, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-add-decision-during-planning
def test_todo_add_decision_during_planning() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    _run(run_id="run-0001", run_type="planning", status="running")
    decision = todo_add_decision(task, lock, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-add-decision-planning-non-user-allowed
def test_todo_add_decision_planning_non_user_allowed() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = todo_add_decision(task, lock, actor_role="agent")
    # During planning, _active_stage_lock_decision allows any actor
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-add-decision-wrong-stage
def test_todo_add_decision_wrong_stage() -> None:
    task = _task(status_stage="implemented")
    decision = todo_add_decision(task, None, actor_role="user")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-add-decision-active-stage-blocks
def test_todo_add_decision_active_stage_blocks() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="implementing", run_id="run-0001")
    decision = todo_add_decision(task, lock, actor_role="user")
    assert decision.ok is False


# -- todo_toggle_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-toggle-decision-ok
def test_todo_toggle_decision_ok() -> None:
    task = _task(status_stage="draft")
    decision = todo_toggle_decision(task, None, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-toggle-during-implementation
def test_todo_toggle_during_implementation() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="implementing", run_id="run-0001")
    decision = todo_toggle_decision(task, lock, actor_role="implementer")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-toggle-validation-denied
def test_todo_toggle_validation_denied() -> None:
    task = _task(status_stage="implemented")
    lock = _lock(stage="validating", run_id="run-0001")
    decision = todo_toggle_decision(task, lock, actor_role="user")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-toggle-done-denied
def test_todo_toggle_done_denied() -> None:
    task = _task(status_stage="done")
    decision = todo_toggle_decision(task, None, actor_role="user")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-toggle-cancelled-denied
def test_todo_toggle_cancelled_denied() -> None:
    task = _task(status_stage="cancelled")
    decision = todo_toggle_decision(task, None, actor_role="user")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-todo-toggle-non-user-denied
def test_todo_toggle_non_user_denied() -> None:
    task = _task(status_stage="draft")
    decision = todo_toggle_decision(task, None, actor_role="implementer")
    assert decision.ok is False


# -- question_add_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-add-ok
def test_question_add_ok() -> None:
    task = _task(status_stage="draft")
    decision = question_add_decision(task, None, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-add-during-planning-user
def test_question_add_during_planning_user() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = question_add_decision(task, lock, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-add-planning-non-user-allowed
def test_question_add_planning_non_user_allowed() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = question_add_decision(task, lock, actor_role="agent")
    # _active_stage_lock_decision allows any actor during planning
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-add-wrong-stage
def test_question_add_wrong_stage() -> None:
    task = _task(status_stage="approved")
    decision = question_add_decision(task, None, actor_role="user")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-add-wrong-active-stage
def test_question_add_wrong_active_stage() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="implementing", run_id="run-0001")
    decision = question_add_decision(task, lock, actor_role="user")
    assert decision.ok is False


# -- question_mutation_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-mutation-ok
def test_question_mutation_ok() -> None:
    task = _task(status_stage="plan_review")
    decision = question_mutation_decision(task, None, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-mutation-planning-user-ok
def test_question_mutation_planning_user_ok() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = question_mutation_decision(task, lock, actor_role="user")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-mutation-planning-non-user-allowed
def test_question_mutation_planning_non_user_allowed() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = question_mutation_decision(task, lock, actor_role="agent")
    # _active_stage_lock_decision allows any actor during planning
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-question-mutation-wrong-stage
def test_question_mutation_wrong_stage() -> None:
    task = _task(status_stage="approved")
    decision = question_mutation_decision(task, None, actor_role="user")
    assert decision.ok is False


# -- plan_propose_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-propose-ok
def test_plan_propose_ok() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    decision = plan_propose_decision(task, lock, run=run)
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-propose-no-lock
def test_plan_propose_no_lock() -> None:
    task = _task(status_stage="draft")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    decision = plan_propose_decision(task, None, run=run)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-propose-no-run
def test_plan_propose_no_run() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = plan_propose_decision(task, lock, run=None)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-propose-run-not-running
def test_plan_propose_run_not_running() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="planning", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="planning", status="finished")
    decision = plan_propose_decision(task, lock, run=run)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-propose-wrong-stage
def test_plan_propose_wrong_stage() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="planning", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="planning", status="running")
    decision = plan_propose_decision(task, lock, run=run)
    assert decision.ok is False


# -- plan_approve_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-approve-ok
def test_plan_approve_ok() -> None:
    task = _task(status_stage="plan_review")
    decision = plan_approve_decision(task, None)
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-approve-wrong-stage
def test_plan_approve_wrong_stage() -> None:
    task = _task(status_stage="draft")
    decision = plan_approve_decision(task, None)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-approve-locked
def test_plan_approve_locked() -> None:
    task = _task(status_stage="plan_review")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = plan_approve_decision(task, lock)
    assert decision.ok is False


# -- plan_revise_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-revise-ok
def test_plan_revise_ok() -> None:
    task = _task(status_stage="plan_review")
    decision = plan_revise_decision(task, None)
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-revise-wrong-stage
def test_plan_revise_wrong_stage() -> None:
    task = _task(status_stage="draft")
    decision = plan_revise_decision(task, None)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-plan-revise-locked
def test_plan_revise_locked() -> None:
    task = _task(status_stage="plan_review")
    lock = _lock(stage="planning", run_id="run-0001")
    decision = plan_revise_decision(task, lock)
    assert decision.ok is False


# -- implementation_mutation_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-implementation-mutation-ok
def test_implementation_mutation_ok() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="implementing", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="implementation", status="running")
    decision = implementation_mutation_decision(task, lock, run=run, action="log")
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-implementation-mutation-no-lock
def test_implementation_mutation_no_lock() -> None:
    task = _task(status_stage="approved")
    run = _run(run_id="run-0001", run_type="implementation", status="running")
    decision = implementation_mutation_decision(task, None, run=run, action="log")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-implementation-mutation-no-run
def test_implementation_mutation_no_run() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="implementing", run_id="run-0001")
    decision = implementation_mutation_decision(task, lock, run=None, action="log")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-implementation-mutation-run-not-running
def test_implementation_mutation_run_not_running() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="implementing", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="implementation", status="finished")
    decision = implementation_mutation_decision(task, lock, run=run, action="log")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-implementation-mutation-wrong-stage
def test_implementation_mutation_wrong_stage() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="implementing", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="implementation", status="running")
    decision = implementation_mutation_decision(task, lock, run=run, action="log")
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-implementation-mutation-lock-run-id-mismatch
def test_implementation_mutation_lock_run_id_mismatch() -> None:
    task = _task(status_stage="approved")
    lock = _lock(stage="implementing", run_id="run-0001")
    run = _run(run_id="run-9999", run_type="implementation", status="running")
    decision = implementation_mutation_decision(task, lock, run=run, action="log")
    assert decision.ok is False


# -- validation_check_decision --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-validation-check-ok
def test_validation_check_ok() -> None:
    task = _task(status_stage="implemented")
    lock = _lock(stage="validating", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="validation", status="running")
    decision = validation_check_decision(task, lock, run=run)
    assert decision.ok is True


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-validation-check-no-lock
def test_validation_check_no_lock() -> None:
    task = _task(status_stage="implemented")
    run = _run(run_id="run-0001", run_type="validation", status="running")
    decision = validation_check_decision(task, None, run=run)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-validation-check-no-run
def test_validation_check_no_run() -> None:
    task = _task(status_stage="implemented")
    lock = _lock(stage="validating", run_id="run-0001")
    decision = validation_check_decision(task, lock, run=None)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-validation-check-run-not-running
def test_validation_check_run_not_running() -> None:
    task = _task(status_stage="implemented")
    lock = _lock(stage="validating", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="validation", status="finished")
    decision = validation_check_decision(task, lock, run=run)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-validation-check-wrong-stage
def test_validation_check_wrong_stage() -> None:
    task = _task(status_stage="draft")
    lock = _lock(stage="validating", run_id="run-0001")
    run = _run(run_id="run-0001", run_type="validation", status="running")
    decision = validation_check_decision(task, lock, run=run)
    assert decision.ok is False


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-validation-check-lock-run-id-mismatch
def test_validation_check_lock_run_id_mismatch() -> None:
    task = _task(status_stage="implemented")
    lock = _lock(stage="validating", run_id="run-0001")
    run = _run(run_id="run-9999", run_type="validation", status="running")
    decision = validation_check_decision(task, lock, run=run)
    assert decision.ok is False


# -- require_known_actor_role --


def test_require_known_actor_role_valid() -> None:
    assert require_known_actor_role("planner") == "planner"
    assert require_known_actor_role("implementer") == "implementer"
    assert require_known_actor_role("user") == "user"


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-unknown-actor-roles-are-rejected
def test_require_known_actor_role_invalid() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unsupported actor role"):
        require_known_actor_role("admin")


# -- Decision properties --


# sw: f=specs/behavior/features/domain_policies/domain-policies.feature
# sw: s=@bdd-domain-policies-decision-reason-property
def test_decision_reason_property() -> None:
    d = Decision(allowed=True, code="OK", message="test msg")
    assert d.reason == "test msg"
