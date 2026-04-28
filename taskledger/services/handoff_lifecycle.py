"""Handoff lifecycle operations."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.domain.models import ActorRef, HarnessRef, TaskHandoffRecord
from taskledger.errors import LaunchError
from taskledger.services.actors import resolve_actor, resolve_harness
from taskledger.storage.task_store import (
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
    updated = replace(
        handoff,
        status="claimed",
        claim_run_id=new_run_id,
        released_lock_id=released_lock_id,
        claimed_at=utc_now_iso(),
        claimed_by=resolved_actor,
        claimed_in_harness=resolved_harness,
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
            updated = replace(updated, released_lock_id=released_lock_id)
    elif handoff.lock_policy == "release" and handoff.source_run_id:
        task = resolve_task(workspace_root, task_id)
        lock = resolve_lock(workspace_root, task.id)
        if lock and lock.run_id == handoff.source_run_id:
            from taskledger.services.phase5_lock_transfer import release_lock

            release_lock(workspace_root, task.id, lock.lock_id)
            released_lock_id = lock.lock_id
            updated = replace(updated, released_lock_id=released_lock_id)

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

    updated = replace(
        handoff,
        status="closed",
        summary=reason or handoff.summary,
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

    updated = replace(
        handoff,
        status="cancelled",
        summary=reason or handoff.summary,
    )

    save_handoff(workspace_root, updated)
    return updated
