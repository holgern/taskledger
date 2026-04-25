"""Tests for handoff lifecycle operations."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from taskledger.api.handoff import create_handoff, list_all_handoffs
from taskledger.api.project import init_project
from taskledger.api.tasks import create_task
from taskledger.domain.models import ActorRef
from taskledger.errors import LaunchError
from taskledger.services.handoff_lifecycle import (
    cancel_handoff,
    claim_handoff,
    close_handoff,
)


def test_handoff_creation():
    """Test creating a handoff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        result = create_handoff(
            workspace,
            "task-0001",
            mode="implementation",
            intended_actor_name="alice",
            summary="Implement feature X",
        )
        
        assert result["handoff_id"].startswith("handoff-")
        assert result["status"] == "open"
        assert result["mode"] == "implementation"
        assert result["intended_actor_name"] == "alice"


def test_handoff_claim():
    """Test claiming a handoff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        handoff = create_handoff(
            workspace, "task-0001", mode="implementation"
        )
        
        claimed = claim_handoff(
            workspace, "task-0001", handoff["handoff_id"]
        )
        
        assert claimed.status == "claimed"
        assert claimed.claimed_by is not None
        assert claimed.claimed_at is not None


def test_handoff_close():
    """Test closing a handoff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        handoff = create_handoff(
            workspace, "task-0001", mode="implementation"
        )
        
        claim_handoff(workspace, "task-0001", handoff["handoff_id"])
        closed = close_handoff(
            workspace, "task-0001", handoff["handoff_id"], reason="Complete"
        )
        
        assert closed.status == "closed"


def test_handoff_cancel():
    """Test cancelling a handoff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        handoff = create_handoff(
            workspace, "task-0001", mode="implementation"
        )
        
        cancelled = cancel_handoff(
            workspace, "task-0001", handoff["handoff_id"], reason="No longer needed"
        )
        
        assert cancelled.status == "cancelled"


def test_cannot_claim_already_claimed():
    """Test that claiming twice fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        handoff = create_handoff(
            workspace, "task-0001", mode="implementation"
        )
        
        claim_handoff(workspace, "task-0001", handoff["handoff_id"])
        
        with pytest.raises(LaunchError, match="Cannot claim"):
            claim_handoff(
                workspace, "task-0001", handoff["handoff_id"]
            )


def test_actor_intent_validation():
    """Test that actor intent is validated on claim."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        handoff = create_handoff(
            workspace,
            "task-0001",
            mode="implementation",
            intended_actor_name="alice",
        )
        
        wrong_actor = ActorRef(
            actor_type="user", actor_name="bob"
        )
        
        with pytest.raises(LaunchError, match="mismatch"):
            claim_handoff(
                workspace,
                "task-0001",
                handoff["handoff_id"],
                actor=wrong_actor,
            )


def test_handoff_list():
    """Test listing handoffs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        create_handoff(workspace, "task-0001", mode="implementation")
        create_handoff(workspace, "task-0001", mode="validation")
        create_handoff(workspace, "task-0001", mode="review")
        
        handoffs = list_all_handoffs(workspace, "task-0001")
        
        assert len(handoffs) == 3


def test_handoff_modes():
    """Test different handoff modes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        modes = ["planning", "implementation", "validation", "review", "delivery"]
        for mode in modes:
            result = create_handoff(workspace, "task-0001", mode=mode)
            assert result["mode"] == mode


def test_handoff_with_summary():
    """Test creating handoff with summary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        summary = "Implement login feature with OAuth support"
        result = create_handoff(
            workspace,
            "task-0001",
            mode="implementation",
            summary=summary,
        )
        
        assert result["summary"] == summary


def test_handoff_list_empty_task():
    """Test listing handoffs for task with no handoffs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        handoffs = list_all_handoffs(workspace, "task-0001")
        
        assert len(handoffs) == 0


def test_handoff_lifecycle_sequence():
    """Test full handoff lifecycle: create -> claim -> close."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        init_project(workspace)
        create_task(workspace, title="Test Task", description="Test", slug="task-0001")
        
        # Create
        h = create_handoff(
            workspace,
            "task-0001",
            mode="implementation",
            summary="Work item"
        )
        assert h["status"] == "open"
        handoff_id = h["handoff_id"]
        
        # Claim
        claimed = claim_handoff(workspace, "task-0001", handoff_id)
        assert claimed.status == "claimed"
        
        # Close
        closed = close_handoff(
            workspace,
            "task-0001",
            handoff_id,
            reason="Work completed"
        )
        assert closed.status == "closed"

