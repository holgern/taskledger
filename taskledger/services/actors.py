"""Actor and harness identity resolution."""

from __future__ import annotations

import getpass
import os
import socket
import sys
from pathlib import Path
from typing import Literal

from taskledger.domain.models import ActorRef, HarnessRef
from taskledger.domain.states import (
    normalize_actor_role,
    normalize_actor_type,
    normalize_harness_kind,
)
from taskledger.ids import next_project_id
from taskledger.storage.task_store import load_actor_state, load_harness_state


def _int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _owner_pid_from_env() -> int | None:
    return _int_env("TASKLEDGER_OWNER_PID") or _int_env("TASKLEDGER_HARNESS_PID")


def _is_harness_context(*, session_id: str | None, harness_id: str | None) -> bool:
    return bool(
        session_id
        or harness_id
        or os.getenv("TASKLEDGER_HARNESS")
        or os.getenv("PI_VERSION")
        or os.getenv("CODEX_VERSION")
        or os.getenv("OPENCODE_VERSION")
    )


def _resolve_pids(
    *,
    tool: str | None,
    session_id: str | None,
    harness_id: str | None,
) -> tuple[int | None, int | None, Literal["owner", "command", "unverifiable_harness"]]:
    """Return (pid, command_pid, pid_scope) based on context."""
    command_pid = os.getpid()
    owner_pid = _owner_pid_from_env()
    harness_context = _is_harness_context(session_id=session_id, harness_id=harness_id)
    if owner_pid is not None:
        return owner_pid, command_pid, "owner"
    if harness_context:
        return None, command_pid, "unverifiable_harness"
    return command_pid, command_pid, "owner"


def resolve_actor(
    *,
    actor_type: str | None = None,
    actor_name: str | None = None,
    role: str | None = None,
    tool: str | None = None,
    session_id: str | None = None,
    harness_id: str | None = None,
    workspace_root: Path | None = None,
) -> ActorRef:
    """
    Resolve actor identity with fallback order:
    1. Explicit parameters
    2. Environment variables
    3. Stored state (actor.yaml)
    4. Auto-detect from environment
    5. Safe default
    """

    # 1. Use explicit params if provided
    if actor_type and actor_name:
        pid, command_pid, pid_scope = _resolve_pids(
            tool=tool,
            session_id=session_id,
            harness_id=harness_id,
        )
        return ActorRef(
            actor_type=normalize_actor_type(actor_type),
            actor_name=actor_name,
            role=normalize_actor_role(role) if role else None,
            tool=tool,
            session_id=session_id,
            harness_id=harness_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    # 2. Check environment variables
    env_actor_type = os.getenv("TASKLEDGER_ACTOR_TYPE")
    env_actor_name = os.getenv("TASKLEDGER_ACTOR_NAME")
    env_role = os.getenv("TASKLEDGER_ACTOR_ROLE")
    env_harness = os.getenv("TASKLEDGER_HARNESS")
    env_session_id = os.getenv("TASKLEDGER_SESSION_ID")
    resolved_role = env_role or role

    if env_actor_type or env_actor_name:
        resolved_session_id = env_session_id or session_id
        resolved_harness_id = harness_id or env_harness
        pid, command_pid, pid_scope = _resolve_pids(
            tool=tool,
            session_id=resolved_session_id,
            harness_id=resolved_harness_id,
        )
        return ActorRef(
            actor_type=normalize_actor_type(env_actor_type or actor_type or "agent"),
            actor_name=env_actor_name or actor_name or "taskledger",
            role=normalize_actor_role(resolved_role) if resolved_role else None,
            tool=tool,
            session_id=resolved_session_id,
            harness_id=resolved_harness_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    # 3. Check stored state
    if workspace_root is not None:
        stored = load_actor_state(workspace_root)
        if stored is not None:
            resolved_session_id = stored.session_id or session_id
            resolved_tool = stored.tool or tool
            pid, command_pid, pid_scope = _resolve_pids(
                tool=resolved_tool,
                session_id=resolved_session_id,
                harness_id=harness_id,
            )
            return ActorRef(
                actor_type=stored.actor_type,
                actor_name=stored.actor_name,
                role=stored.role,
                tool=resolved_tool,
                session_id=resolved_session_id,
                harness_id=harness_id,
                host=socket.gethostname(),
                pid=pid,
                command_pid=command_pid,
                pid_scope=pid_scope,
            )

    # 4. Auto-detect from environment
    if os.getenv("OPENCODE_VERSION"):
        resolved_session_id = session_id or os.getenv("TASKLEDGER_SESSION_ID")
        pid, command_pid, pid_scope = _resolve_pids(
            tool="opencode",
            session_id=resolved_session_id,
            harness_id=harness_id,
        )
        return ActorRef(
            actor_type="agent",
            actor_name="opencode",
            tool="opencode",
            session_id=resolved_session_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    if os.getenv("CODEX_VERSION"):
        resolved_session_id = session_id or os.getenv("TASKLEDGER_SESSION_ID")
        pid, command_pid, pid_scope = _resolve_pids(
            tool="codex",
            session_id=resolved_session_id,
            harness_id=harness_id,
        )
        return ActorRef(
            actor_type="agent",
            actor_name="codex",
            tool="codex",
            session_id=resolved_session_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    if os.getenv("PI_VERSION"):
        resolved_session_id = session_id or os.getenv("TASKLEDGER_SESSION_ID")
        pid, command_pid, pid_scope = _resolve_pids(
            tool="pi",
            session_id=resolved_session_id,
            harness_id=harness_id,
        )
        return ActorRef(
            actor_type="agent",
            actor_name="pi",
            tool="pi",
            session_id=resolved_session_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    if os.getenv("GITHUB_ACTIONS") == "true":
        resolved_session_id = session_id or os.getenv("GITHUB_RUN_ID")
        pid, command_pid, pid_scope = _resolve_pids(
            tool="github-actions",
            session_id=resolved_session_id,
            harness_id=harness_id,
        )
        return ActorRef(
            actor_type="system",
            actor_name="github-actions",
            tool="github-actions",
            session_id=resolved_session_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    if sys.stdin.isatty() and not any(
        [
            os.getenv("OPENCODE_VERSION"),
            os.getenv("CODEX_VERSION"),
            os.getenv("PI_VERSION"),
            os.getenv("GITHUB_ACTIONS"),
        ]
    ):
        pid, command_pid, pid_scope = _resolve_pids(
            tool=None,
            session_id=session_id,
            harness_id=harness_id,
        )
        return ActorRef(
            actor_type="user",
            actor_name=getpass.getuser() or "user",
            session_id=session_id,
            host=socket.gethostname(),
            pid=pid,
            command_pid=command_pid,
            pid_scope=pid_scope,
        )

    # 5. Safe default
    pid, command_pid, pid_scope = _resolve_pids(
        tool=tool,
        session_id=session_id,
        harness_id=harness_id,
    )
    return ActorRef(
        actor_type="agent",
        actor_name="taskledger",
        tool=tool,
        session_id=session_id,
        host=socket.gethostname(),
        pid=pid,
        command_pid=command_pid,
        pid_scope=pid_scope,
    )


def resolve_harness(
    *,
    name: str | None = None,
    kind: str | None = None,
    session_id: str | None = None,
    cwd: Path | None = None,
    workspace_root: Path | None = None,
) -> HarnessRef:
    """
    Resolve harness identity with fallback order:
    1. Explicit parameters
    2. Environment variables
    3. Stored state (harness.yaml)
    4. Auto-detect from environment
    5. Safe default
    """

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

    # Check stored state
    if workspace_root is not None:
        stored = load_harness_state(workspace_root)
        if stored is not None:
            harness_id = next_project_id("harness", [])
            return HarnessRef(
                harness_id=harness_id,
                name=stored.name,
                kind=stored.kind,
                session_id=stored.session_id or session_id,
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
