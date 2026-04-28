"""Tests for taskledger.storage.contexts."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths
from taskledger.storage.contexts import (
    delete_context,
    load_contexts,
    rename_context,
    resolve_context,
    save_context,
    save_context_entry,
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
        taskledger_dir=project_dir,
    )


def test_load_contexts_empty(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    assert load_contexts(paths) == []


def test_save_context_and_load(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(
        paths,
        name="Build Context",
        memory_refs=("mem-001",),
        file_refs=("src/main.py",),
    )
    assert entry.slug == "build-context"
    assert entry.memory_refs == ("mem-001",)
    assert entry.file_refs == ("src/main.py",)

    loaded = load_contexts(paths)
    assert len(loaded) == 1
    assert loaded[0].id == entry.id


def test_save_context_summary(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(
        paths,
        name="Summary Check",
        memory_refs=("m1", "m2"),
        file_refs=("f1",),
        directory_refs=("d1", "d2", "d3"),
        item_refs=("i1",),
        inline_texts=("text1",),
        loop_latest_refs=("l1", "l2"),
    )
    assert "memories=2" in (entry.summary or "")
    assert "files=1" in (entry.summary or "")
    assert "dirs=3" in (entry.summary or "")
    assert "items=1" in (entry.summary or "")
    assert "inline=1" in (entry.summary or "")
    assert "loop=2" in (entry.summary or "")


def test_save_context_upsert_same_slug(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry1 = save_context(paths, name="My Ctx", memory_refs=("m1",))
    entry2 = save_context(paths, name="My Ctx", file_refs=("f1",))
    assert entry2.id == entry1.id
    assert entry2.file_refs == ("f1",)
    loaded = load_contexts(paths)
    assert len(loaded) == 1


def test_save_context_creates_context_json_file(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="File Check")
    context_json = paths.project_dir / entry.path
    assert context_json.exists()
    import json

    data = json.loads(context_json.read_text())
    assert data["id"] == entry.id


def test_resolve_context_by_id(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="Resolve ID")
    resolved = resolve_context(paths, entry.id)
    assert resolved.id == entry.id


def test_resolve_context_by_slug(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    save_context(paths, name="Resolve Slug")
    resolved = resolve_context(paths, "resolve-slug")
    assert resolved.slug == "resolve-slug"


def test_resolve_context_by_name(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    save_context(paths, name="Exact Name")
    resolved = resolve_context(paths, "Exact Name")
    assert resolved.name == "Exact Name"


def test_resolve_context_unknown_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(LaunchError, match="Unknown project context"):
        resolve_context(paths, "does-not-exist")


def test_save_context_entry(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="Entry Test", memory_refs=("m1",))
    from dataclasses import replace

    updated = replace(entry, memory_refs=("m1", "m2"))
    result = save_context_entry(paths, updated)
    assert result.memory_refs == ("m1", "m2")
    loaded = load_contexts(paths)
    assert len(loaded) == 1
    assert loaded[0].memory_refs == ("m1", "m2")


def test_rename_context(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="Old Name")
    renamed = rename_context(paths, entry.id, "New Name")
    assert renamed.name == "New Name"
    assert renamed.slug == "new-name"
    # Verify old slug resolves
    resolved = resolve_context(paths, "new-name")
    assert resolved.id == entry.id


def test_rename_context_duplicate_name_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    save_context(paths, name="First")
    entry2 = save_context(paths, name="Second")
    with pytest.raises(LaunchError, match="already exists with name"):
        rename_context(paths, entry2.id, "First")


def test_rename_context_cleans_old_file(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="Old File")
    old_json = paths.project_dir / entry.path
    assert old_json.exists()
    rename_context(paths, entry.id, "New File")
    assert not old_json.exists()


def test_delete_context(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="Delete Me")
    context_json = paths.project_dir / entry.path
    assert context_json.exists()
    deleted = delete_context(paths, entry.id)
    assert deleted.id == entry.id
    assert load_contexts(paths) == []
    assert not context_json.exists()


def test_delete_context_file_already_gone(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    entry = save_context(paths, name="Ghost")
    context_json = paths.project_dir / entry.path
    context_json.unlink()
    # Should still succeed (delete_context loads from index, then removes)
    deleted = delete_context(paths, entry.id)
    assert deleted.id == entry.id
