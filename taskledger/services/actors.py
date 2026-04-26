"""Actor and harness identity resolution."""

from __future__ import annotations

import getpass
import os
import socket
import sys
from pathlib import Path

from taskledger.domain.states import normalize_actor_type, normalize_actor_role, normalize_harness_kind
from taskledger.domain.models import ActorRef, HarnessRef
from taskledger.ids import next_project_id


def resolve_actor(
    *,
    actor_type: str | None = None,
    actor_name: str | None = None,
    role: str | None = None,
    tool: str | None = None,
    session_id: str | None = None,
    harness_id: str | None = None,
) -> ActorRef:
    """
    Resolve actor identity with fallback order:
    1. Explicit parameters
    2. Environment variables
    3. Auto-detect from environment
    4. Safe default
    """

    # 1. Use explicit params if provided
    if actor_type and actor_name:
        return ActorRef(
            actor_type=normalize_actor_type(actor_type),
            actor_name=actor_name,
            role=normalize_actor_role(role) if role else None,
            tool=tool,
            session_id=session_id,
            harness_id=harness_id,
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    # 2. Check environment variables
    env_actor_type = os.getenv("TASKLEDGER_ACTOR_TYPE")
    env_actor_name = os.getenv("TASKLEDGER_ACTOR_NAME")
    env_role = os.getenv("TASKLEDGER_ACTOR_ROLE")
    env_harness = os.getenv("TASKLEDGER_HARNESS")
    env_session_id = os.getenv("TASKLEDGER_SESSION_ID")

    if env_actor_type or env_actor_name:
        return ActorRef(
            actor_type=normalize_actor_type(env_actor_type or actor_type or "agent"),
            actor_name=env_actor_name or actor_name or "taskledger",
            role=normalize_actor_role(env_role or role) if (env_role or role) else None,
            tool=tool,
            session_id=env_session_id or session_id,
            harness_id=harness_id or env_harness,
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    # 3. Auto-detect from environment
    if os.getenv("OPENCODE_VERSION"):
        return ActorRef(
            actor_type="agent",
            actor_name="opencode",
            tool="opencode",
            session_id=session_id,
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    if os.getenv("CODEX_VERSION"):
        return ActorRef(
            actor_type="agent",
            actor_name="codex",
            tool="codex",
            session_id=session_id,
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    if os.getenv("PI_VERSION"):
        return ActorRef(
            actor_type="agent",
            actor_name="pi",
            tool="pi",
            session_id=session_id,
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    if os.getenv("GITHUB_ACTIONS") == "true":
        return ActorRef(
            actor_type="system",
            actor_name="github-actions",
            tool="github-actions",
            session_id=session_id or os.getenv("GITHUB_RUN_ID"),
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    if sys.stdin.isatty() and not any(
        [
            os.getenv("OPENCODE_VERSION"),
            os.getenv("CODEX_VERSION"),
            os.getenv("PI_VERSION"),
            os.getenv("GITHUB_ACTIONS"),
        ]
    ):
        return ActorRef(
            actor_type="user",
            actor_name=getpass.getuser() or "user",
            session_id=session_id,
            host=socket.gethostname(),
            pid=os.getpid(),
        )

    # 4. Safe default
    return ActorRef(
        actor_type="agent",
        actor_name="taskledger",
        tool=tool,
        session_id=session_id,
        host=socket.gethostname(),
        pid=os.getpid(),
    )


def resolve_harness(
    *,
    name: str | None = None,
    kind: str | None = None,
    session_id: str | None = None,
    cwd: Path | None = None,
) -> HarnessRef:
    """Resolve harness identity with fallback order."""

    # Use explicit params if provided
    if name:
        harness_id = next_project_id("harness", [])
        return HarnessRef(
            harness_id=harness_id,
            name=name,
            kind=normalize_harness_kind(kind or "unknown"),
            session_id=session_id,
            working_directory=str(cwd) if cwd else None,
        )

    # Check environment
    env_harness = os.getenv("TASKLEDGER_HARNESS")
    if env_harness:
        harness_id = next_project_id("harness", [])
        return HarnessRef(
            harness_id=harness_id,
            name=env_harness,
            kind=normalize_harness_kind(kind or "unknown"),
            session_id=session_id or os.getenv("TASKLEDGER_SESSION_ID"),
            working_directory=str(cwd) if cwd else None,
        )

    # Auto-detect
    if os.getenv("OPENCODE_VERSION"):
        harness_id = next_project_id("harness", [])
        return HarnessRef(
            harness_id=harness_id,
            name="opencode",
            kind="agent_harness",
            session_id=session_id,
        )

    if os.getenv("CODEX_VERSION"):
        harness_id = next_project_id("harness", [])
        return HarnessRef(
            harness_id=harness_id,
            name="codex",
            kind="agent_harness",
            session_id=session_id,
        )

    if os.getenv("GITHUB_ACTIONS") == "true":
        harness_id = next_project_id("harness", [])
        return HarnessRef(
            harness_id=harness_id,
            name="github-actions",
            kind="ci",
            session_id=session_id or os.getenv("GITHUB_RUN_ID"),
        )

    # Default
    harness_id = next_project_id("harness", [])
    return HarnessRef(
        harness_id=harness_id,
        name="unknown",
        kind="unknown",
        session_id=session_id,
        working_directory=str(cwd) if cwd else None,
    )
