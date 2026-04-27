"""Tests for storage version enforcement, migration framework, and migrate CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskledger.domain.models import (
    ActiveActorState,
    ActiveHarnessState,
    ActiveTaskState,
    DependencyRequirement,
    FileLink,
    TaskTodo,
)
from taskledger.domain.states import (
    TASKLEDGER_RECORD_SCHEMA_VERSION,
    TASKLEDGER_SCHEMA_VERSION,
    TASKLEDGER_STORAGE_LAYOUT_VERSION,
    TASKLEDGER_V2_FILE_VERSION,
)
from taskledger.errors import LaunchError
from taskledger.storage.meta import StorageMeta, read_storage_meta, write_storage_meta

# ---------------------------------------------------------------------------
# Phase 2: Storage version constants
# ---------------------------------------------------------------------------


class TestStorageVersionConstants:
    def test_storage_layout_version_is_2(self) -> None:
        assert TASKLEDGER_STORAGE_LAYOUT_VERSION == 2

    def test_record_schema_version_matches_schema_version(self) -> None:
        assert TASKLEDGER_RECORD_SCHEMA_VERSION == TASKLEDGER_SCHEMA_VERSION

    def test_schema_version_is_1(self) -> None:
        assert TASKLEDGER_SCHEMA_VERSION == 1

    def test_v2_file_version(self) -> None:
        assert TASKLEDGER_V2_FILE_VERSION == "v2"


# ---------------------------------------------------------------------------
# Phase 2: StorageMeta read/write
# ---------------------------------------------------------------------------


class TestStorageMeta:
    def test_roundtrip(self, tmp_path: Path) -> None:
        meta = StorageMeta(created_with_taskledger="0.1.0")
        write_storage_meta(tmp_path, meta)
        loaded = read_storage_meta(tmp_path)
        assert loaded is not None
        assert loaded.storage_layout_version == TASKLEDGER_STORAGE_LAYOUT_VERSION
        assert loaded.record_schema_version == TASKLEDGER_RECORD_SCHEMA_VERSION
        assert loaded.created_with_taskledger == "0.1.0"

    def test_missing_storage_yaml_returns_none(self, tmp_path: Path) -> None:
        assert read_storage_meta(tmp_path) is None

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        tl_dir = tmp_path / ".taskledger"
        tl_dir.mkdir()
        (tl_dir / "storage.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
        with pytest.raises(LaunchError, match="Invalid storage.yaml"):
            read_storage_meta(tmp_path)

    def test_non_mapping_raises(self, tmp_path: Path) -> None:
        tl_dir = tmp_path / ".taskledger"
        tl_dir.mkdir()
        (tl_dir / "storage.yaml").write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(LaunchError, match="expected mapping"):
            read_storage_meta(tmp_path)

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        tl_dir = tmp_path / ".taskledger"
        tl_dir.mkdir()
        (tl_dir / "storage.yaml").write_text(
            "storage_layout_version: 2\n", encoding="utf-8"
        )
        with pytest.raises(LaunchError, match="Missing or invalid"):
            read_storage_meta(tmp_path)

    def test_to_dict_keys(self) -> None:
        meta = StorageMeta()
        d = meta.to_dict()
        assert "storage_layout_version" in d
        assert "record_schema_version" in d
        assert "created_with_taskledger" in d
        assert "created_at" in d


# ---------------------------------------------------------------------------
# Phase 2: Active state models include file_version
# ---------------------------------------------------------------------------


class TestActiveStateFileVersion:
    def test_active_task_state_has_file_version(self) -> None:
        state = ActiveTaskState(task_id="task-0001")
        d = state.to_dict()
        assert d["file_version"] == TASKLEDGER_V2_FILE_VERSION

    def test_active_actor_state_has_file_version(self) -> None:
        state = ActiveActorState()
        d = state.to_dict()
        assert d["file_version"] == TASKLEDGER_V2_FILE_VERSION

    def test_active_harness_state_has_file_version(self) -> None:
        state = ActiveHarnessState()
        d = state.to_dict()
        assert d["file_version"] == TASKLEDGER_V2_FILE_VERSION

    def test_active_task_roundtrip_with_file_version(self) -> None:
        state = ActiveTaskState(task_id="task-0001")
        restored = ActiveTaskState.from_dict(state.to_dict())
        assert restored.file_version == TASKLEDGER_V2_FILE_VERSION

    def test_active_task_legacy_no_file_version(self) -> None:
        data = {
            "schema_version": 1,
            "object_type": "active_task",
            "task_id": "task-0001",
            "activated_at": "2026-01-01T00:00:00+00:00",
            "activated_by": {"actor_type": "agent", "actor_name": "test"},
        }
        state = ActiveTaskState.from_dict(data)
        assert state.file_version == TASKLEDGER_V2_FILE_VERSION


# ---------------------------------------------------------------------------
# Phase 2: Sidecar model version enforcement
# ---------------------------------------------------------------------------


class TestSidecarVersionEnforcement:
    def test_todo_accepts_valid_v2(self) -> None:
        todo = TaskTodo.from_dict(
            {
                "id": "todo-0001",
                "text": "test",
                "schema_version": 1,
                "object_type": "todo",
                "file_version": "v2",
            }
        )
        assert todo.id == "todo-0001"

    def test_todo_accepts_legacy_no_version(self) -> None:
        todo = TaskTodo.from_dict({"id": "todo-0001", "text": "test"})
        assert todo.id == "todo-0001"

    def test_todo_rejects_too_new_schema(self) -> None:
        with pytest.raises(LaunchError, match="schema too new"):
            TaskTodo.from_dict(
                {
                    "id": "todo-0001",
                    "text": "test",
                    "schema_version": 99,
                    "object_type": "todo",
                    "file_version": "v2",
                }
            )

    def test_todo_rejects_wrong_object_type(self) -> None:
        with pytest.raises(LaunchError, match="Invalid object_type"):
            TaskTodo.from_dict(
                {
                    "id": "todo-0001",
                    "text": "test",
                    "schema_version": 1,
                    "object_type": "wrong",
                    "file_version": "v2",
                }
            )

    def test_todo_rejects_wrong_file_version(self) -> None:
        with pytest.raises(LaunchError, match="Unsupported file version"):
            TaskTodo.from_dict(
                {
                    "id": "todo-0001",
                    "text": "test",
                    "schema_version": 1,
                    "object_type": "todo",
                    "file_version": "v99",
                }
            )

    def test_link_accepts_valid_v2(self) -> None:
        link = FileLink.from_dict(
            {
                "path": "/foo.py",
                "schema_version": 1,
                "object_type": "link",
                "file_version": "v2",
            }
        )
        assert link.path == "/foo.py"

    def test_link_accepts_legacy_no_version(self) -> None:
        link = FileLink.from_dict({"path": "/foo.py"})
        assert link.path == "/foo.py"

    def test_link_rejects_too_new_schema(self) -> None:
        with pytest.raises(LaunchError, match="schema too new"):
            FileLink.from_dict(
                {
                    "path": "/foo.py",
                    "schema_version": 99,
                    "object_type": "link",
                    "file_version": "v2",
                }
            )

    def test_requirement_accepts_valid_v2(self) -> None:
        req = DependencyRequirement.from_dict(
            {
                "task_id": "task-0001",
                "schema_version": 1,
                "object_type": "requirement",
                "file_version": "v2",
            }
        )
        assert req.task_id == "task-0001"

    def test_requirement_accepts_legacy_no_version(self) -> None:
        req = DependencyRequirement.from_dict({"task_id": "task-0001"})
        assert req.task_id == "task-0001"

    def test_requirement_rejects_too_new_schema(self) -> None:
        with pytest.raises(LaunchError, match="schema too new"):
            DependencyRequirement.from_dict(
                {
                    "task_id": "task-0001",
                    "schema_version": 99,
                    "object_type": "requirement",
                    "file_version": "v2",
                }
            )


# ---------------------------------------------------------------------------
# Phase 2: Init writes storage.yaml
# ---------------------------------------------------------------------------


class TestInitWritesStorageYaml:
    def test_init_creates_storage_yaml(self, tmp_path: Path) -> None:
        from taskledger.storage.init import init_project_state

        _paths, created = init_project_state(tmp_path)
        storage_yaml = tmp_path / ".taskledger" / "storage.yaml"
        assert storage_yaml.exists()
        assert any("storage.yaml" in c for c in created)

    def test_init_idempotent(self, tmp_path: Path) -> None:
        from taskledger.storage.init import init_project_state

        init_project_state(tmp_path)
        _paths, created2 = init_project_state(tmp_path)
        assert not any("storage.yaml" in c for c in created2)


# ---------------------------------------------------------------------------
# Phase 3: Migration framework
# ---------------------------------------------------------------------------


class TestMigrationFramework:
    def test_required_layout_migrations_empty_when_current(self) -> None:
        from taskledger.storage.migrations import required_layout_migrations

        result = required_layout_migrations(
            TASKLEDGER_STORAGE_LAYOUT_VERSION,
            TASKLEDGER_STORAGE_LAYOUT_VERSION,
        )
        assert result == []

    def test_required_layout_migrations_raises_for_unsupported(self) -> None:
        from taskledger.storage.migrations import required_layout_migrations

        with pytest.raises(LaunchError, match="No migration path"):
            required_layout_migrations(1, TASKLEDGER_STORAGE_LAYOUT_VERSION)

    def test_scan_records_empty_on_fresh_workspace(self, tmp_path: Path) -> None:
        from taskledger.storage.init import init_project_state
        from taskledger.storage.migrations import scan_records_for_migration

        init_project_state(tmp_path)
        needed = scan_records_for_migration(tmp_path)
        assert needed == []


# ---------------------------------------------------------------------------
# Phase 3: Migrate CLI commands
# ---------------------------------------------------------------------------


class TestMigrateCLI:
    def test_migrate_status_no_storage(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from taskledger.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--root", str(tmp_path), "migrate", "status"])
        assert result.exit_code == 0
        assert "No storage.yaml" in result.output

    def test_migrate_status_up_to_date(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from taskledger.cli import app
        from taskledger.storage.init import init_project_state

        init_project_state(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["--root", str(tmp_path), "migrate", "status"])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_migrate_plan_no_storage(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from taskledger.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--root", str(tmp_path), "migrate", "plan"])
        assert result.exit_code == 0
        assert "No storage.yaml" in result.output

    def test_migrate_apply_no_storage(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from taskledger.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--root", str(tmp_path), "migrate", "apply"])
        assert result.exit_code == 2

    def test_migrate_apply_up_to_date(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from taskledger.cli import app
        from taskledger.storage.init import init_project_state

        init_project_state(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app, ["--root", str(tmp_path), "migrate", "apply", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_migrate_commands_in_inventory(self) -> None:
        from taskledger.command_inventory import COMMAND_METADATA

        assert "migrate status" in COMMAND_METADATA
        assert "migrate plan" in COMMAND_METADATA
        assert "migrate apply" in COMMAND_METADATA


# ---------------------------------------------------------------------------
# Phase 3: Doctor schema checks storage layout version
# ---------------------------------------------------------------------------


class TestDoctorSchemaLayoutVersion:
    def test_doctor_schema_missing_storage_yaml(self, tmp_path: Path) -> None:
        from taskledger.storage.init import init_project_state

        init_project_state(tmp_path)
        # Remove storage.yaml
        storage_yaml = tmp_path / ".taskledger" / "storage.yaml"
        if storage_yaml.exists():
            storage_yaml.unlink()

        from taskledger.services.doctor_v2 import inspect_v2_schema

        result = inspect_v2_schema(tmp_path)
        assert not result["healthy"]
        assert any("storage.yaml" in e for e in result["errors"])

    def test_doctor_schema_up_to_date(self, tmp_path: Path) -> None:
        from taskledger.services.doctor_v2 import inspect_v2_schema
        from taskledger.storage.init import init_project_state

        init_project_state(tmp_path)
        result = inspect_v2_schema(tmp_path)
        # Should not have storage layout errors if up to date
        layout_errors = [
            e
            for e in result["errors"]
            if "layout" in e.lower() or "storage" in e.lower()
        ]
        assert layout_errors == []
