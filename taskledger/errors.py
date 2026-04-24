from __future__ import annotations

from collections.abc import Mapping, Sequence


class TaskledgerError(Exception):
    """Base class for public taskledger errors."""

    exit_code = 1
    error_type = "TaskledgerError"

    def __init__(
        self,
        message: str,
        *,
        exit_code: int | None = None,
        error_type: str | None = None,
        remediation: Sequence[str] | None = None,
        data: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.taskledger_exit_code = (
            exit_code if exit_code is not None else self.exit_code
        )
        if error_type is not None:
            self.taskledger_error_type = error_type
        self.taskledger_remediation = list(remediation or ())
        self.taskledger_data = dict(data or {})


class UnsupportedAgentError(TaskledgerError):
    """Raised when the requested agent is not supported."""


class AgentNotInstalledError(TaskledgerError):
    """Raised when the requested agent executable is not available."""


class LaunchError(TaskledgerError):
    """Raised when the child process cannot be prepared or started."""

    error_type = "LaunchError"


class InvalidPromptError(TaskledgerError):
    """Raised when prompt input is empty or invalid."""

    exit_code = 11
    error_type = "ValidationError"


class NotFound(TaskledgerError):
    exit_code = 10
    error_type = "NotFound"


class ValidationError(TaskledgerError):
    exit_code = 11
    error_type = "ValidationError"


class InvalidStageTransition(TaskledgerError):
    exit_code = 20
    error_type = "InvalidStageTransition"


class ApprovalRequired(TaskledgerError):
    exit_code = 21
    error_type = "ApprovalRequired"


class DependencyIncomplete(TaskledgerError):
    exit_code = 22
    error_type = "DependencyIncomplete"


class LockConflict(TaskledgerError):
    exit_code = 30
    error_type = "LockConflict"


class StaleLockRequiresBreak(TaskledgerError):
    exit_code = 31
    error_type = "StaleLockRequiresBreak"


class StorageCorruption(TaskledgerError):
    exit_code = 40
    error_type = "StorageCorruption"


class IndexRebuildFailed(TaskledgerError):
    exit_code = 41
    error_type = "IndexRebuildFailed"
