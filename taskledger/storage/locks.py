from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from taskledger.domain.models import TaskLock
from taskledger.errors import LaunchError
from taskledger.storage.atomic import atomic_create_text, atomic_write_text
from taskledger.storage.common import read_text


def write_lock(path: Path, lock: TaskLock) -> None:
    atomic_create_text(
        path,
        yaml.safe_dump(lock.to_dict(), sort_keys=False, allow_unicode=True),
    )


def update_lock(path: Path, lock: TaskLock) -> None:
    """Update an existing lock, or create if it doesn't exist."""
    atomic_write_text(
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


def lock_is_expired(lock: TaskLock, *, now: datetime | None = None) -> bool:
    if lock.expires_at is None:
        return False
    try:
        expires_at = datetime.fromisoformat(lock.expires_at)
    except ValueError as exc:
        raise LaunchError(
            f"Invalid lock expiration on {lock.task_id} "
            f"({lock.lock_id}): {lock.expires_at}"
        ) from exc
    reference = now or datetime.now(timezone.utc)
    return expires_at < reference


def lock_status(lock: TaskLock | None) -> dict[str, object]:
    if lock is None:
        return {
            "active": False,
            "expired": False,
            "holder": None,
            "stage": None,
            "run_id": None,
            "created_at": None,
            "expires_at": None,
        }
    return {
        "active": True,
        "expired": lock_is_expired(lock),
        "holder": lock.holder.to_dict(),
        "stage": lock.stage,
        "run_id": lock.run_id,
        "created_at": lock.created_at,
        "expires_at": lock.expires_at,
    }
