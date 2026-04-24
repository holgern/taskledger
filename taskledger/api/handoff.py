from pathlib import Path
from typing import Any

from taskledger.domain.models import TaskHandoffRecord, ActorRef, HarnessRef
from taskledger.services.handoff import render_handoff
from taskledger.storage.v2 import (
    list_handoffs,
    resolve_handoff,
    save_handoff,
)


def create_handoff(
    workspace_root: Path,
    task_ref: str,
    *,
    mode: str,
    intended_actor_type: str | None = None,
    intended_actor_name: str | None = None,
    intended_harness: str | None = None,
    summary: str | None = None,
    next_action: str | None = None,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> dict[str, object]:
    """Create and save a handoff record."""
    from taskledger.services.actors import resolve_actor, resolve_harness
    from taskledger.ids import next_project_id
    
    resolved_actor = actor or resolve_actor()
    resolved_harness = harness or resolve_harness()
    
    # Get existing handoff IDs for this task
    existing_handoffs = list_handoffs(workspace_root, task_ref)
    existing_ids = [h.handoff_id for h in existing_handoffs]
    
    handoff_id = next_project_id('handoff', existing_ids)
    handoff = TaskHandoffRecord(
        handoff_id=handoff_id,
        task_id=task_ref,
        mode=mode,
        status="open",
        created_by=resolved_actor,
        created_from_harness=resolved_harness,
        intended_actor_type=intended_actor_type,
        intended_actor_name=intended_actor_name,
        intended_harness=intended_harness,
        summary=summary,
        next_action=next_action,
    )
    save_handoff(workspace_root, handoff)
    return handoff.to_dict()


def list_all_handoffs(workspace_root: Path, task_ref: str) -> list[dict[str, object]]:
    """List all handoffs for a task."""
    handoffs = list_handoffs(workspace_root, task_ref)
    return [h.to_dict() for h in handoffs]


def show_handoff(
    workspace_root: Path,
    task_ref: str,
    handoff_ref: str,
) -> dict[str, object]:
    """Get a specific handoff."""
    handoff = resolve_handoff(workspace_root, task_ref, handoff_ref)
    return handoff.to_dict()


def claim_handoff_api(
    workspace_root: Path,
    task_ref: str,
    handoff_ref: str,
    *,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
    new_run_id: str | None = None,
) -> dict[str, object]:
    """Claim a handoff, transitioning from 'open' to 'claimed'."""
    from taskledger.services.handoff_lifecycle import claim_handoff
    
    handoff = claim_handoff(
        workspace_root,
        task_ref,
        handoff_ref,
        actor=actor,
        harness=harness,
        new_run_id=new_run_id,
    )
    return handoff.to_dict()


def close_handoff_api(
    workspace_root: Path,
    task_ref: str,
    handoff_ref: str,
    *,
    actor: ActorRef | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    """Close a handoff, transitioning from 'claimed' to 'closed'."""
    from taskledger.services.handoff_lifecycle import close_handoff
    
    handoff = close_handoff(
        workspace_root,
        task_ref,
        handoff_ref,
        actor=actor,
        reason=reason,
    )
    return handoff.to_dict()


def cancel_handoff_api(
    workspace_root: Path,
    task_ref: str,
    handoff_ref: str,
    *,
    actor: ActorRef | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    """Cancel a handoff, transitioning from 'open' to 'cancelled'."""
    from taskledger.services.handoff_lifecycle import cancel_handoff
    
    handoff = cancel_handoff(
        workspace_root,
        task_ref,
        handoff_ref,
        actor=actor,
        reason=reason,
    )
    return handoff.to_dict()


__all__ = [
    "render_handoff",
    "create_handoff",
    "list_all_handoffs",
    "show_handoff",
    "claim_handoff_api",
    "close_handoff_api",
    "cancel_handoff_api",
]

