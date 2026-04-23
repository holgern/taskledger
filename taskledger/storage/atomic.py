from __future__ import annotations

import os
import tempfile
from pathlib import Path

from taskledger.errors import LaunchError


def atomic_write_text(path: Path, contents: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            handle.write(contents)
            temp_path = Path(handle.name)
        temp_path.replace(path)
    except OSError as exc:
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
    except OSError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc
