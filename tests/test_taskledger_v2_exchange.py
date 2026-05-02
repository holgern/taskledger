from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any, cast

import pytest
from click.testing import Result
from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.errors import LaunchError
from taskledger.exchange import (
    ARCHIVE_KIND,
    ARCHIVE_VERSION,
    MANIFEST_MEMBER,
    MAX_ARCHIVE_MEMBERS,
    MAX_MANIFEST_BYTES,
    MAX_PAYLOAD_BYTES,
    PAYLOAD_MEMBER,
    read_project_archive,
)


def _make_runner() -> CliRunner:
    return CliRunner()


runner = _make_runner()


def _init_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--cwd", str(tmp_path), "init"])
    assert result.exit_code == 0


def _copy_project_uuid(src_root: Path, dst_root: Path) -> None:
    """Make dst_root project use the same project_uuid as src_root."""
    from shutil import copy2

    copy2(src_root / "taskledger.toml", dst_root / "taskledger.toml")


def _json(result: Result) -> dict[str, Any]:
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    payload_dict = cast(dict[str, Any], payload)
    assert payload_dict.get("ok") is True
    return payload_dict


def _valid_archive_bytes(*, extra_members: int = 0) -> bytes:
    project_uuid = "11111111-1111-1111-1111-111111111111"
    payload_dict = {
        "version": 3,
        "project_uuid": project_uuid,
        "ledgers": [],
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()
    manifest_dict = {
        "kind": ARCHIVE_KIND,
        "archive_version": ARCHIVE_VERSION,
        "project": {"uuid": project_uuid},
        "payload": {"sha256": payload_sha},
    }
    manifest_bytes = json.dumps(manifest_dict).encode("utf-8")

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        manifest_info = tarfile.TarInfo(MANIFEST_MEMBER)
        manifest_info.size = len(manifest_bytes)
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))

        payload_info = tarfile.TarInfo(PAYLOAD_MEMBER)
        payload_info.size = len(payload_bytes)
        tar.addfile(payload_info, io.BytesIO(payload_bytes))

        for index in range(extra_members):
            data = b"x"
            info = tarfile.TarInfo(f"extra/{index}.txt")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

    return out.getvalue()


def _archive_with_member_sizes(*, manifest_size: int, payload_size: int) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        manifest_data = b"x" * manifest_size
        manifest_info = tarfile.TarInfo(MANIFEST_MEMBER)
        manifest_info.size = len(manifest_data)
        tar.addfile(manifest_info, io.BytesIO(manifest_data))

        payload_data = b"x" * payload_size
        payload_info = tarfile.TarInfo(PAYLOAD_MEMBER)
        payload_info.size = len(payload_data)
        tar.addfile(payload_info, io.BytesIO(payload_data))

    return out.getvalue()


def _write_archive(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def _task_lock_paths(project_root: Path, task_id: str) -> list[Path]:
    return sorted(
        (project_root / ".taskledger" / "ledgers").glob(f"*/tasks/{task_id}/lock.yaml")
    )


def _prepare_active_implementation(project_root: Path, *, slug: str) -> None:
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(project_root),
                "task",
                "create",
                slug,
                "--description",
                "Prepare an active implementation for archive transfer tests.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(project_root), "task", "activate", slug]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(project_root), "plan", "start"]).exit_code == 0
    )
    plan_text = """---
goal: Test cross-machine import behavior.
acceptance_criteria:
  - id: ac-0001
    text: Import state can be resumed.
    mandatory: true
todos:
  - id: todo-0001
    text: Keep implementation running.
    mandatory: true
    validation_hint: taskledger next-action
---

# Plan

Keep implementation open for export/import testing.
"""
    assert (
        runner.invoke(
            app,
            ["--cwd", str(project_root), "plan", "propose", "--text", plan_text],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(project_root),
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved for exchange import tests.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(project_root), "implement", "start"]).exit_code
        == 0
    )


def test_export_and_import_include_v2_state(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)
    _copy_project_uuid(source_root, dest_root)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "task",
                "create",
                "migrate-v2",
                "--description",
                "Migrate taskledger to v2.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "plan", "start", "--task", "migrate-v2"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "plan",
                "propose",
                "--task",
                "migrate-v2",
                "--text",
                "## Goal\n\nShip export support.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "handoff",
                "create",
                "--task",
                "migrate-v2",
                "--mode",
                "implementation",
                "--summary",
                "Continue elsewhere.",
            ],
        ).exit_code
        == 0
    )

    # Export archive to file
    archive_path = tmp_path / "export.tar.gz"
    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "export", str(archive_path)],
    )
    assert export_result.exit_code == 0
    assert archive_path.exists()

    # JSON export returns metadata, not full payload
    json_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "--json", "export", "--overwrite"],
    )
    json_payload = _json(json_result)
    assert "project_uuid" in json_payload["result"]
    assert "v2" not in json_payload["result"]  # metadata only

    # Import into dest
    import_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "import", str(archive_path)],
    )
    assert import_result.exit_code == 0

    show_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "--json", "task", "show", "--task", "migrate-v2"],
    )
    task_payload = _json(show_result)
    assert task_payload["result"]["task"]["latest_plan_version"] == 1
    handoffs = _json(
        runner.invoke(
            app,
            [
                "--cwd",
                str(dest_root),
                "--json",
                "handoff",
                "list",
                "--task",
                "migrate-v2",
            ],
        )
    )
    assert handoffs["result"]["handoffs"][0]["mode"] == "implementation"


def test_export_and_import_include_release_records(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)
    _copy_project_uuid(source_root, dest_root)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "task",
                "create",
                "release-boundary",
                "--description",
                "Create a release boundary task.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["--cwd", str(source_root), "task", "activate", "release-boundary"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["--cwd", str(source_root), "plan", "start"]).exit_code == 0
    )
    plan_text = """---
goal: Finish a release boundary task.
acceptance_criteria:
  - id: ac-0001
    text: Release boundary task is done.
todos:
  - id: todo-0001
    text: Finish the boundary task.
    validation_hint: python -c "print('ok')"
---

# Plan

Finish the boundary task.
"""
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "plan", "propose", "--text", plan_text],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "plan",
                "approve",
                "--version",
                "1",
                "--actor",
                "user",
                "--note",
                "Approved.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "implement", "start"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "implement",
                "change",
                "--path",
                "taskledger/exchange.py",
                "--kind",
                "edit",
                "--summary",
                "Prepared exchange release coverage.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "todo",
                "done",
                "todo-0001",
                "--evidence",
                "python -c print('ok')",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "implement",
                "finish",
                "--summary",
                "Implemented release boundary.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["--cwd", str(source_root), "validate", "start"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "validate",
                "check",
                "--criterion",
                "ac-0001",
                "--status",
                "pass",
                "--evidence",
                "python -c print('ok')",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "validate",
                "finish",
                "--result",
                "passed",
                "--summary",
                "Validated release boundary.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "release",
                "tag",
                "0.4.1",
                "--at-task",
                "release-boundary",
                "--note",
                "0.4.1 released",
            ],
        ).exit_code
        == 0
    )

    # Export archive
    archive_path = tmp_path / "release-export.tar.gz"
    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "export", str(archive_path)],
    )
    assert export_result.exit_code == 0

    # Import into dest
    import_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "import", str(archive_path)],
    )
    assert import_result.exit_code == 0

    show_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "--json", "release", "show", "0.4.1"],
    )
    payload = _json(show_result)
    assert payload["result"]["release"]["boundary_task_id"] == "task-0001"


def test_import_replace_quarantines_lock_and_allows_resume(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)
    _copy_project_uuid(source_root, dest_root)
    _prepare_active_implementation(source_root, slug="portable-import")

    archive_path = tmp_path / "portable-import.tar.gz"
    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "export", str(archive_path)],
    )
    assert export_result.exit_code == 0, export_result.stdout

    import_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "import", str(archive_path), "--replace"],
    )
    assert import_result.exit_code == 0, import_result.stdout

    assert not _task_lock_paths(dest_root, "task-0001")
    imported_lock_audits = sorted(
        (dest_root / ".taskledger" / "ledgers").glob(
            "*/tasks/task-0001/audit/imported-lock-*.yaml"
        )
    )
    assert imported_lock_audits

    next_action_payload = _json(
        runner.invoke(app, ["--cwd", str(dest_root), "--json", "next-action"])
    )
    assert next_action_payload["result"]["action"] == "implement-resume"


def test_import_replace_lock_policy_keep_restores_lock(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)
    _copy_project_uuid(source_root, dest_root)
    _prepare_active_implementation(source_root, slug="keep-lock-import")

    archive_path = tmp_path / "keep-lock-import.tar.gz"
    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "export", str(archive_path)],
    )
    assert export_result.exit_code == 0, export_result.stdout

    import_result = runner.invoke(
        app,
        [
            "--cwd",
            str(dest_root),
            "import",
            str(archive_path),
            "--replace",
            "--lock-policy",
            "keep",
        ],
    )
    assert import_result.exit_code == 0, import_result.stdout
    assert _task_lock_paths(dest_root, "task-0001")


def test_import_archive_rejects_different_project_uuid_without_mutation(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    _init_project(source_root)
    _init_project(dest_root)

    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(source_root),
                "task",
                "create",
                "source-task",
                "--description",
                "Source state.",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "--cwd",
                str(dest_root),
                "task",
                "create",
                "dest-task",
                "--description",
                "Destination state.",
            ],
        ).exit_code
        == 0
    )

    archive_path = tmp_path / "mismatch.tar.gz"
    export_result = runner.invoke(
        app,
        ["--cwd", str(source_root), "export", str(archive_path)],
    )
    assert export_result.exit_code == 0, export_result.stdout

    import_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "import", str(archive_path), "--replace"],
    )
    assert import_result.exit_code != 0
    assert "Project UUID mismatch" in (import_result.stdout + import_result.stderr)

    dest_task_result = runner.invoke(
        app,
        ["--cwd", str(dest_root), "task", "show", "--task", "dest-task"],
    )
    assert dest_task_result.exit_code == 0, dest_task_result.stdout


def test_read_project_archive_rejects_too_many_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "too-many-members.tar.gz"
    data = _valid_archive_bytes(extra_members=MAX_ARCHIVE_MEMBERS - 1)
    _write_archive(archive_path, data)

    with pytest.raises(LaunchError, match="too many members"):
        read_project_archive(archive_path)


def test_read_project_archive_rejects_oversized_manifest(tmp_path: Path) -> None:
    archive_path = tmp_path / "oversized-manifest.tar.gz"
    data = _archive_with_member_sizes(
        manifest_size=MAX_MANIFEST_BYTES + 1,
        payload_size=128,
    )
    _write_archive(archive_path, data)

    with pytest.raises(LaunchError, match="manifest is too large"):
        read_project_archive(archive_path)


def test_read_project_archive_rejects_oversized_payload(tmp_path: Path) -> None:
    archive_path = tmp_path / "oversized-payload.tar.gz"
    data = _archive_with_member_sizes(
        manifest_size=128,
        payload_size=MAX_PAYLOAD_BYTES + 1,
    )
    _write_archive(archive_path, data)

    with pytest.raises(LaunchError, match="payload is too large"):
        read_project_archive(archive_path)
