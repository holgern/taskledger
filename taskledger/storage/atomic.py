from __future__ import annotations

from pathlib import Path

from ledgercore.atomic import (
    atomic_create_text as _atomic_create_text,
)
from ledgercore.atomic import (
    atomic_write_text as _atomic_write_text,
)
from ledgercore.errors import AtomicWriteError

from taskledger.errors import LaunchError

_FAST_TEST_IO_ENV = "TASKLEDGER_TEST_FAST_IO"


def atomic_write_text(path: Path, contents: str) -> None:
    try:
        _atomic_write_text(
            path,
            contents,
            normalize=False,
            fsync=True,
            fast_io_env_var=_FAST_TEST_IO_ENV,
        )
    except AtomicWriteError as exc:
        raise LaunchError(f"Failed to atomically write {path}: {exc}") from exc


def atomic_create_text(path: Path, contents: str) -> None:
    try:
        _atomic_create_text(
            path,
            contents,
            fsync=True,
            fast_io_env_var=_FAST_TEST_IO_ENV,
        )
    except AtomicWriteError as exc:
        message = str(exc)
        if "Target already exists" in message:
            raise LaunchError(f"Lock already exists: {path}") from exc
        raise LaunchError(f"Failed to create {path}: {exc}") from exc
