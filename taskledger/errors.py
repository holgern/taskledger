from __future__ import annotations


class TaskledgerError(Exception):
    """Base class for public taskledger errors."""


class UnsupportedAgentError(TaskledgerError):
    """Raised when the requested agent is not supported."""


class AgentNotInstalledError(TaskledgerError):
    """Raised when the requested agent executable is not available."""


class LaunchError(TaskledgerError):
    """Raised when the child process cannot be prepared or started."""


class InvalidPromptError(TaskledgerError):
    """Raised when prompt input is empty or invalid."""
