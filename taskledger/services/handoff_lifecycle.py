"""Handoff lifecycle operations."""

from __future__ import annotations

from pathlib import Path

from taskledger.domain.models import ActorRef, HarnessRef, TaskHandoffRecord
from taskledger.errors import LaunchError
from taskledger.services.actors import resolve_actor, resolve_harness
from taskledger.storage.v2 import (
    resolve_handoff,
    resolve_lock,
    resolve_task,
    save_handoff,
)
from taskledger.timeutils import utc_now_iso


def claim_handoff(
    workspace_root: Path,
    task_id: str,
    handoff_id: str,
    *,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
    new_run_id: str | None = None,
) -> TaskHandoffRecord:
    """Claim a handoff, transitioning from 'open' to 'claimed'."""
    handoff = resolve_handoff(workspace_root, task_id, handoff_id)

    if handoff.status != "open":
        raise LaunchError(f"Cannot claim handoff in status {handoff.status}")

    resolved_actor = actor or resolve_actor()
    resolved_harness = harness or resolve_harness()

    # Check intent match if specified
    if (
        handoff.intended_actor_type
        and handoff.intended_actor_type != resolved_actor.actor_type
    ):
        raise LaunchError(
            f"Actor type mismatch: handoff intended for {handoff.intended_actor_type}, "
            f"but claiming as {resolved_actor.actor_type}"
        )
    if (
        handoff.intended_actor_name
        and handoff.intended_actor_name != resolved_actor.actor_name
    ):
        raise LaunchError(
            f"Actor name mismatch: handoff intended for {handoff.intended_actor_name}, "
            f"but claiming as {resolved_actor.actor_name}"
        )
    if (
        handoff.intended_harness
        and handoff.intended_harness != "any"
        and handoff.intended_harness != resolved_harness.name
    ):
        raise LaunchError(
            f"Harness mismatch: handoff intended for {handoff.intended_harness}, "
            f"but claiming in {resolved_harness.name}"
        )

    # Create new handoff with claim info
    released_lock_id = handoff.released_lock_id
    updated = TaskHandoffRecord(
        handoff_id=handoff.handoff_id,
        task_id=handoff.task_id,
        mode=handoff.mode,
        status="claimed",
        created_at=handoff.created_at,
        created_by=handoff.created_by,
        created_from_harness=handoff.created_from_harness,
        intended_actor_type=handoff.intended_actor_type,
        intended_actor_name=handoff.intended_actor_name,
        intended_harness=handoff.intended_harness,
        source_run_id=handoff.source_run_id,
        resumes_run_id=handoff.resumes_run_id,
        claim_run_id=new_run_id,
        lock_policy=handoff.lock_policy,
        released_lock_id=released_lock_id,
        claimed_at=utc_now_iso(),
        claimed_by=resolved_actor,
        claimed_in_harness=resolved_harness,
        summary=handoff.summary,
        next_action=handoff.next_action,
        context_body=handoff.context_body,
    )

    # Handle lock transfer if applicable
    if handoff.lock_policy == "transfer" and handoff.source_run_id:
        task = resolve_task(workspace_root, task_id)
        lock = resolve_lock(workspace_root, task.id)
        if lock and lock.run_id == handoff.source_run_id:
            from taskledger.services.phase5_lock_transfer import transfer_lock

            transfer_lock(
                workspace_root, task.id, lock.lock_id, resolved_actor, resolved_harness
            )
            released_lock_id = lock.lock_id
            updated = TaskHandoffRecord(
                handoff_id=updated.handoff_id,
                task_id=updated.task_id,
                mode=updated.mode,
                status=updated.status,
                created_at=updated.created_at,
                created_by=updated.created_by,
                created_from_harness=updated.created_from_harness,
                intended_actor_type=updated.intended_actor_type,
                intended_actor_name=updated.intended_actor_name,
                intended_harness=updated.intended_harness,
                source_run_id=updated.source_run_id,
                resumes_run_id=updated.resumes_run_id,
                claim_run_id=updated.claim_run_id,
                lock_policy=updated.lock_policy,
                released_lock_id=released_lock_id,
                claimed_at=updated.claimed_at,
                claimed_by=updated.claimed_by,
                claimed_in_harness=updated.claimed_in_harness,
                summary=updated.summary,
                next_action=updated.next_action,
                context_body=updated.context_body,
            )
    elif handoff.lock_policy == "release" and handoff.source_run_id:
        task = resolve_task(workspace_root, task_id)
        lock = resolve_lock(workspace_root, task.id)
        if lock and lock.run_id == handoff.source_run_id:
            from taskledger.services.phase5_lock_transfer import release_lock

            release_lock(workspace_root, task.id, lock.lock_id)
            released_lock_id = lock.lock_id
            updated = TaskHandoffRecord(
                handoff_id=updated.handoff_id,
                task_id=updated.task_id,
                mode=updated.mode,
                status=updated.status,
                created_at=updated.created_at,
                created_by=updated.created_by,
                created_from_harness=updated.created_from_harness,
                intended_actor_type=updated.intended_actor_type,
                intended_actor_name=updated.intended_actor_name,
                intended_harness=updated.intended_harness,
                source_run_id=updated.source_run_id,
                resumes_run_id=updated.resumes_run_id,
                claim_run_id=updated.claim_run_id,
                lock_policy=updated.lock_policy,
                released_lock_id=released_lock_id,
                claimed_at=updated.claimed_at,
                claimed_by=updated.claimed_by,
                claimed_in_harness=updated.claimed_in_harness,
                summary=updated.summary,
                next_action=updated.next_action,
                context_body=updated.context_body,
            )

    save_handoff(workspace_root, updated)
    return updated


def close_handoff(
    workspace_root: Path,
    task_id: str,
    handoff_id: str,
    *,
    actor: ActorRef | None = None,
    reason: str | None = None,
) -> TaskHandoffRecord:
    """Close a handoff, transitioning from 'claimed' to 'closed'."""
    handoff = resolve_handoff(workspace_root, task_id, handoff_id)

    if handoff.status not in ("open", "claimed"):
        raise LaunchError(f"Cannot close handoff in status {handoff.status}")

    resolved_actor = actor or resolve_actor()
    _ = resolved_actor  # used for actor resolution side-effect

    updated = TaskHandoffRecord(
        handoff_id=handoff.handoff_id,
        task_id=handoff.task_id,
        mode=handoff.mode,
        status="closed",
        created_at=handoff.created_at,
        created_by=handoff.created_by,
        created_from_harness=handoff.created_from_harness,
        intended_actor_type=handoff.intended_actor_type,
        intended_actor_name=handoff.intended_actor_name,
        intended_harness=handoff.intended_harness,
        source_run_id=handoff.source_run_id,
        resumes_run_id=handoff.resumes_run_id,
        claim_run_id=handoff.claim_run_id,
        lock_policy=handoff.lock_policy,
        released_lock_id=handoff.released_lock_id,
        claimed_at=handoff.claimed_at,
        claimed_by=handoff.claimed_by,
        claimed_in_harness=handoff.claimed_in_harness,
        summary=reason or handoff.summary,
        next_action=handoff.next_action,
        context_body=handoff.context_body,
    )

    save_handoff(workspace_root, updated)
    return updated


def cancel_handoff(
    workspace_root: Path,
    task_id: str,
    handoff_id: str,
    *,
    actor: ActorRef | None = None,
    reason: str | None = None,
) -> TaskHandoffRecord:
    """Cancel a handoff, transitioning from 'open' to 'cancelled'."""
    handoff = resolve_handoff(workspace_root, task_id, handoff_id)

    if handoff.status != "open":
        raise LaunchError(f"Cannot cancel handoff in status {handoff.status}")

    resolved_actor = actor or resolve_actor()
    _ = resolved_actor  # used for actor resolution side-effect

    updated = TaskHandoffRecord(
        handoff_id=handoff.handoff_id,
        task_id=handoff.task_id,
        mode=handoff.mode,
        status="cancelled",
        created_at=handoff.created_at,
        created_by=handoff.created_by,
        created_from_harness=handoff.created_from_harness,
        intended_actor_type=handoff.intended_actor_type,
        intended_actor_name=handoff.intended_actor_name,
        intended_harness=handoff.intended_harness,
        source_run_id=handoff.source_run_id,
        resumes_run_id=handoff.resumes_run_id,
        claim_run_id=handoff.claim_run_id,
        lock_policy=handoff.lock_policy,
        released_lock_id=handoff.released_lock_id,
        claimed_at=handoff.claimed_at,
        claimed_by=handoff.claimed_by,
        claimed_in_harness=handoff.claimed_in_harness,
        summary=reason or handoff.summary,
        next_action=handoff.next_action,
        context_body=handoff.context_body,
    )

    save_handoff(workspace_root, updated)
    return updated
