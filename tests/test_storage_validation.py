"""Tests for taskledger.storage.validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths
from taskledger.storage.validation import (
    append_validation_record,
    load_validation_records,
    remove_validation_records,
    save_validation_records,
    validation_records_dir,
    validation_records_index_path,
)


def _paths(tmp_path: Path) -> ProjectPaths:
    project_dir = tmp_path / ".taskledger"
    return ProjectPaths(
        workspace_root=tmp_path,
        project_dir=project_dir,
        config_path=project_dir / "project.toml",
        repos_dir=project_dir / "repos",
        repo_index_path=project_dir / "repos" / "index.json",
        workflows_dir=project_dir / "workflows",
        workflow_index_path=project_dir / "workflows" / "index.json",
        memories_dir=project_dir / "memories",
        contexts_dir=project_dir / "contexts",
        context_index_path=project_dir / "contexts" / "index.json",
        items_dir=project_dir / "items",
        stages_dir=project_dir / "stages",
        stage_index_path=project_dir / "stages" / "index.json",
        runs_dir=project_dir / "runs",
    )


def test_validation_records_dir(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    d = validation_records_dir(paths)
    assert d == paths.project_dir / "validation"


def test_validation_records_index_path(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    p = validation_records_index_path(paths)
    assert p == paths.project_dir / "validation" / "index.json"


def test_load_validation_records_no_file(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    assert load_validation_records(paths) == []


def test_append_and_load(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    rec = append_validation_record(
        paths,
        project_item_ref="it-001",
        memory_ref="mem-001",
        kind="acceptance",
        run_id="run-001",
        status="passed",
        verdict="all good",
        notes="manual check",
    )
    assert rec["id"] == "val-0001"
    assert rec["project_item_ref"] == "it-001"
    assert rec["memory_ref"] == "mem-001"
    assert rec["kind"] == "acceptance"
    assert rec["run_id"] == "run-001"
    assert rec["status"] == "passed"
    assert rec["verdict"] == "all good"
    assert rec["notes"] == "manual check"
    assert "created_at" in rec

    loaded = load_validation_records(paths)
    assert len(loaded) == 1
    assert loaded[0]["id"] == "val-0001"


def test_append_minimal(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    rec = append_validation_record(
        paths,
        project_item_ref="it-002",
        memory_ref="mem-002",
        kind="smoke",
    )
    assert "run_id" not in rec
    assert "status" not in rec
    assert "verdict" not in rec
    assert "notes" not in rec


def test_append_with_source(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    rec = append_validation_record(
        paths,
        project_item_ref="it-003",
        memory_ref="mem-003",
        kind="coverage",
        source={"tool": "pytest-cov", "pct": 85},
    )
    assert rec["source"] == {"tool": "pytest-cov", "pct": 85}
    loaded = load_validation_records(paths)
    assert loaded[0]["source"] == {"tool": "pytest-cov", "pct": 85}


def test_multiple_records_increment_id(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    r1 = append_validation_record(paths, project_item_ref="it-1", memory_ref="m1", kind="a")
    r2 = append_validation_record(paths, project_item_ref="it-2", memory_ref="m2", kind="b")
    assert r1["id"] == "val-0001"
    assert r2["id"] == "val-0002"
    assert len(load_validation_records(paths)) == 2


def test_save_and_reload(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    rec = append_validation_record(
        paths, project_item_ref="it-sv", memory_ref="m-sv", kind="save"
    )
    loaded = load_validation_records(paths)
    assert len(loaded) == 1
    # Re-save the same records
    save_validation_records(paths, loaded)
    reloaded = load_validation_records(paths)
    assert len(reloaded) == 1
    assert reloaded[0]["id"] == rec["id"]


def test_remove_validation_records(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    r1 = append_validation_record(paths, project_item_ref="it-r1", memory_ref="m1", kind="a")
    r2 = append_validation_record(paths, project_item_ref="it-r2", memory_ref="m2", kind="b")
    r3 = append_validation_record(paths, project_item_ref="it-r3", memory_ref="m3", kind="c")
    removed = remove_validation_records(paths, ids={r1["id"], r3["id"]})
    assert len(removed) == 2
    remaining = load_validation_records(paths)
    assert len(remaining) == 1
    assert remaining[0]["id"] == r2["id"]


def test_remove_validation_records_empty_ids(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    removed = remove_validation_records(paths, ids=set())
    assert removed == []


def test_remove_validation_records_no_match(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    append_validation_record(paths, project_item_ref="it-x", memory_ref="m-x", kind="a")
    removed = remove_validation_records(paths, ids={"val-9999"})
    assert removed == []
    assert len(load_validation_records(paths)) == 1


def test_load_validation_records_normalizes_missing_optional(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    index_path = validation_records_index_path(paths)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    # Write a raw record with only required fields
    index_path.write_text(json.dumps([{
        "id": "val-0001",
        "created_at": "2026-01-01T00:00:00Z",
        "project_item_ref": "it-raw",
        "memory_ref": "m-raw",
        "kind": "manual",
    }]))
    loaded = load_validation_records(paths)
    assert len(loaded) == 1
    assert loaded[0]["id"] == "val-0001"
    assert "run_id" not in loaded[0]


def test_load_validation_records_rejects_non_string_field(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    index_path = validation_records_index_path(paths)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    index_path.write_text(json.dumps([{
        "id": "val-0001",
        "created_at": "2026-01-01T00:00:00Z",
        "project_item_ref": "it-bad",
        "memory_ref": "m-bad",
        "kind": "manual",
        "status": 123,  # not a string
    }]))
    with pytest.raises(LaunchError, match="must be a string"):
        load_validation_records(paths)


def test_load_validation_records_rejects_empty_required(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    index_path = validation_records_index_path(paths)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    index_path.write_text(json.dumps([{
        "id": "val-0001",
        "created_at": "2026-01-01T00:00:00Z",
        "project_item_ref": "",
        "memory_ref": "m-x",
        "kind": "manual",
    }]))
    with pytest.raises(LaunchError, match="non-empty string"):
        load_validation_records(paths)


def test_load_validation_records_source_not_dict(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    index_path = validation_records_index_path(paths)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    index_path.write_text(json.dumps([{
        "id": "val-0001",
        "created_at": "2026-01-01T00:00:00Z",
        "project_item_ref": "it-src",
        "memory_ref": "m-src",
        "kind": "manual",
        "source": "not-a-dict",
    }]))
    with pytest.raises(LaunchError, match="must be an object"):
        load_validation_records(paths)


def test_load_validation_records_preserves_source_dict(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    index_path = validation_records_index_path(paths)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    index_path.write_text(json.dumps([{
        "id": "val-0001",
        "created_at": "2026-01-01T00:00:00Z",
        "project_item_ref": "it-src2",
        "memory_ref": "m-src2",
        "kind": "manual",
        "source": {"a": 1},
        "notes": "ok",
        "verdict": "pass",
        "status": "done",
        "run_id": "r-1",
    }]))
    loaded = load_validation_records(paths)
    assert loaded[0]["source"] == {"a": 1}
    assert loaded[0]["notes"] == "ok"
    assert loaded[0]["verdict"] == "pass"
    assert loaded[0]["status"] == "done"
    assert loaded[0]["run_id"] == "r-1"
