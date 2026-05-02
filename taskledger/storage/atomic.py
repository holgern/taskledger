from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol

from taskledger.errors import LaunchError


class _SupportsFileno(Protocol):
    def fileno(self) -> int: ...


_FAST_TEST_IO_ENV = "TASKLEDGER_TEST_FAST_IO"


def _durability_fsync_enabled() -> bool:
    return os.environ.get(_FAST_TEST_IO_ENV, "").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }


def _fsync_file(handle: _SupportsFileno) -> None:
    if _durability_fsync_enabled():
        os.fsync(handle.fileno())


def atomic_write_text(path: Path, contents: str) -> None:
    temp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            handle.write(contents)
            handle.flush()
            _fsync_file(handle)
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    except OSError as exc:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise LaunchError(f"Failed to atomically write {path}: {exc}") from exc


def atomic_create_text(path: Path, contents: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as exc:
        raise LaunchError(f"Lock already exists: {path}") from exc
    except OSError as exc:
        raise LaunchError(f"Failed to create {path}: {exc}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(contents)
            handle.flush()
            _fsync_file(handle)
    except OSError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc
    _fsync_directory(path.parent)


def _fsync_directory(path: Path) -> None:
    if not _durability_fsync_enabled():
        return
    if os.name != "posix":
        return
    directory_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
