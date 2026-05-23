from __future__ import annotations

from pathlib import Path

from taskledger.services.storage_locations import (
    build_storage_location_report,
    build_sync_preflight_report,
    build_sync_status_report,
    move_taskledger_storage,
    sync_commit_storage,
)


def storage_where(workspace_root: Path) -> dict[str, object]:
    return build_storage_location_report(workspace_root).to_dict()


def storage_move(
    workspace_root: Path,
    *,
    target: Path,
    mode: str,
    adopt_existing: bool = False,
    force: bool = False,
) -> dict[str, object]:
    return move_taskledger_storage(
        workspace_root,
        target=target,
        mode=mode,
        adopt_existing=adopt_existing,
        force=force,
    ).to_dict()


def sync_preflight(workspace_root: Path) -> dict[str, object]:
    return build_sync_preflight_report(workspace_root).to_dict()


def sync_status(workspace_root: Path) -> dict[str, object]:
    return build_sync_status_report(workspace_root).to_dict()


def sync_commit(workspace_root: Path, *, message: str) -> dict[str, object]:
    return sync_commit_storage(workspace_root, message=message).to_dict()


__all__ = [
    "storage_where",
    "storage_move",
    "sync_preflight",
    "sync_status",
    "sync_commit",
]
