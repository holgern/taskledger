from __future__ import annotations

from pathlib import Path

import yaml

from taskledger.domain.models import TaskLock
from taskledger.errors import LaunchError
from taskledger.storage.atomic import atomic_create_text
from taskledger.storage.common import read_text


def write_lock(path: Path, lock: TaskLock) -> None:
    atomic_create_text(
        path,
        yaml.safe_dump(lock.to_dict(), sort_keys=False, allow_unicode=True),
    )


def read_lock(path: Path) -> TaskLock | None:
    if not path.exists():
        return None
    try:
        payload = yaml.safe_load(read_text(path))
    except yaml.YAMLError as exc:
        raise LaunchError(f"Invalid lock file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LaunchError(f"Invalid lock file {path}: expected mapping.")
    return TaskLock.from_dict(payload)


def remove_lock(path: Path) -> None:
    if not path.exists():
        return
    try:
        path.unlink()
    except OSError as exc:
        raise LaunchError(f"Failed to remove lock {path}: {exc}") from exc
