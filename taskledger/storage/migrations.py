"""Migration framework for taskledger storage layout and record schema changes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from taskledger.domain.states import TASKLEDGER_STORAGE_LAYOUT_VERSION
from taskledger.errors import LaunchError

Record = dict[str, Any]
MigrationFunc = Callable[[Path], None]
RecordMigrationFunc = Callable[[Record], Record]


@dataclass(frozen=True)
class LayoutMigration:
    from_version: int
    to_version: int
    name: str
    apply: MigrationFunc


@dataclass(frozen=True)
class RecordMigration:
    object_type: str
    from_schema_version: int
    to_schema_version: int
    name: str
    apply: RecordMigrationFunc


@dataclass(frozen=True)
class MigrationNeeded:
    path: Path
    object_type: str
    current_version: int
    target_version: int


LAYOUT_MIGRATIONS: tuple[LayoutMigration, ...] = ()

RECORD_MIGRATIONS: tuple[RecordMigration, ...] = ()


def required_layout_migrations(current: int, target: int) -> list[LayoutMigration]:
    migrations: list[LayoutMigration] = []
    version = current
    while version < target:
        match = next(
            (
                migration
                for migration in LAYOUT_MIGRATIONS
                if migration.from_version == version
            ),
            None,
        )
        if match is None:
            raise LaunchError(
                f"No migration path from storage layout {version} to {version + 1}."
            )
        migrations.append(match)
        version = match.to_version
    return migrations


def scan_records_for_migration(
    workspace_root: Path,
) -> list[MigrationNeeded]:
    """Scan all durable records for pending schema migrations.

    Returns a list of records whose schema_version is below the current target.
    """
    from taskledger.storage.v2 import resolve_v2_paths

    paths = resolve_v2_paths(workspace_root)
    needed: list[MigrationNeeded] = []
    if not paths.tasks_dir.exists():
        return needed

    for task_dir in sorted(paths.tasks_dir.glob("task-*")):
        if not task_dir.is_dir():
            continue
        _scan_dir(task_dir / "plans", "plan", needed)
        _scan_dir(task_dir / "questions", "question", needed)
        _scan_dir(task_dir / "runs", "run", needed)
        _scan_dir(task_dir / "changes", "change", needed)
        _scan_dir(task_dir / "todos", "todo", needed)
        _scan_dir(task_dir / "links", "link", needed)
        _scan_dir(task_dir / "requirements", "requirement", needed)
        _scan_dir(task_dir / "handoffs", "handoff", needed)

        task_md = task_dir / "task.md"
        if task_md.exists():
            _scan_file(task_md, "task", needed)

    return needed


def apply_layout_migrations(
    workspace_root: Path,
    current_version: int,
    dry_run: bool = False,
) -> list[str]:
    """Apply layout migrations from current_version
    to TASKLEDGER_STORAGE_LAYOUT_VERSION.

    Returns list of migration names that were applied (or would be applied in dry_run).
    """
    from taskledger.storage.meta import read_storage_meta, write_storage_meta

    migrations = required_layout_migrations(
        current_version, TASKLEDGER_STORAGE_LAYOUT_VERSION
    )
    applied: list[str] = []
    for migration in migrations:
        if not dry_run:
            migration.apply(workspace_root)
        applied.append(migration.name)

    if not dry_run and applied:
        meta = read_storage_meta(workspace_root)
        if meta is not None:
            try:
                from taskledger._version import __version__ as tl_version
            except ImportError:
                tl_version = "unknown"
            from taskledger.timeutils import utc_now_iso

            updated = type(meta)(
                storage_layout_version=TASKLEDGER_STORAGE_LAYOUT_VERSION,
                record_schema_version=meta.record_schema_version,
                created_with_taskledger=meta.created_with_taskledger,
                created_at=meta.created_at,
                last_migrated_with_taskledger=tl_version,
                last_migrated_at=utc_now_iso(),
            )
            write_storage_meta(workspace_root, updated)

    return applied


def _scan_dir(
    directory: Path,
    object_type: str,
    needed: list[MigrationNeeded],
) -> None:
    if not directory.exists():
        return
    for md_file in sorted(directory.glob("*.md")):
        _scan_file(md_file, object_type, needed)


def _scan_file(
    path: Path,
    default_object_type: str,
    needed: list[MigrationNeeded],
) -> None:
    from taskledger.storage.frontmatter import read_markdown_front_matter

    try:
        metadata, _ = read_markdown_front_matter(path)
    except Exception:
        return
    version = metadata.get("schema_version")
    if not isinstance(version, int):
        return
    if version < 1:
        return  # Legacy/unversioned, not a migration candidate
    from taskledger.domain.states import TASKLEDGER_SCHEMA_VERSION

    if version < TASKLEDGER_SCHEMA_VERSION:
        needed.append(
            MigrationNeeded(
                path=path,
                object_type=str(metadata.get("object_type", default_object_type)),
                current_version=version,
                target_version=TASKLEDGER_SCHEMA_VERSION,
            )
        )
