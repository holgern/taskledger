"""Tests for taskledger.storage.memories."""
from __future__ import annotations

from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths
from taskledger.storage.frontmatter import MARKDOWN_FILE_VERSION
from taskledger.storage.memories import (
    create_memory,
    delete_memory,
    load_memories,
    memory_markdown_path,
    read_memory_body,
    refresh_memory,
    rename_memory,
    resolve_memory,
    save_memories,
    update_memory_body,
    update_memory_tags,
    write_memory_body,
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


def test_load_memories_empty(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    assert load_memories(paths) == []


def test_create_and_load_memory(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Test Memory", body="hello world", tags=("a", "b"))
    assert mem.name == "Test Memory"
    assert mem.slug == "test-memory"
    assert "a" in mem.tags and "b" in mem.tags
    assert mem.content_hash is not None
    assert mem.summary == "hello world"

    loaded = load_memories(paths)
    assert len(loaded) == 1
    assert loaded[0].id == mem.id
    assert loaded[0].name == "Test Memory"


def test_create_memory_no_body(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Empty")
    assert mem.summary is None
    assert mem.content_hash is None


def test_create_memory_duplicate_name_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    create_memory(paths, name="My Mem")
    with pytest.raises(LaunchError, match="already exists with name"):
        create_memory(paths, name="My Mem")


def test_resolve_memory_by_id(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Resolve Me")
    resolved = resolve_memory(paths, mem.id)
    assert resolved.id == mem.id


def test_resolve_memory_by_slug(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Resolve Slug")
    resolved = resolve_memory(paths, "resolve-slug")
    assert resolved.id == mem.id


def test_resolve_memory_by_name(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    create_memory(paths, name="Exact Name")
    resolved = resolve_memory(paths, "Exact Name")
    assert resolved.name == "Exact Name"


def test_resolve_memory_unknown_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(LaunchError, match="Unknown project memory"):
        resolve_memory(paths, "does-not-exist")


def test_read_memory_body(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Body Test", body="some content here")
    body = read_memory_body(paths, mem)
    assert "some content here" in body


def test_read_memory_body_missing_file(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Gone")
    # Delete the file manually
    p = memory_markdown_path(paths, mem)
    p.unlink()
    body = read_memory_body(paths, mem)
    assert body == ""


def test_write_memory_body(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Writable", body="old")
    updated = write_memory_body(paths, mem.id, "new body text", source_run_id="run-001")
    assert updated.summary == "new body text"
    assert updated.source_run_id == "run-001"
    # Re-read to verify persistence
    body = read_memory_body(paths, updated)
    assert "new body text" in body


def test_update_memory_body_replace(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Replace", body="original")
    updated = update_memory_body(paths, mem.id, "replaced", mode="replace")
    assert updated.summary == "replaced"


def test_update_memory_body_append(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Append", body="line1")
    updated = update_memory_body(paths, mem.id, "line2", mode="append")
    body = read_memory_body(paths, updated)
    assert "line1" in body
    assert "line2" in body


def test_update_memory_body_prepend(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Prepend", body="line2")
    updated = update_memory_body(paths, mem.id, "line1", mode="prepend")
    body = read_memory_body(paths, updated)
    assert "line1" in body
    assert "line2" in body


def test_update_memory_body_invalid_mode(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Mode", body="x")
    with pytest.raises(LaunchError, match="Unsupported memory update mode"):
        update_memory_body(paths, mem.id, "y", mode="invalid")


def test_refresh_memory(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Refresh", body="initial content")
    # Manually overwrite body on disk
    from taskledger.storage.frontmatter import write_markdown_front_matter
    md_path = memory_markdown_path(paths, mem)
    write_markdown_front_matter(md_path, {"file_version": MARKDOWN_FILE_VERSION, **mem.to_dict()}, "refreshed content")
    refreshed = refresh_memory(paths, mem.id)
    assert refreshed.summary == "refreshed content"


def test_rename_memory(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Old Name", body="content")
    renamed = rename_memory(paths, mem.id, "New Name")
    assert renamed.name == "New Name"
    assert renamed.slug == "new-name"
    # Verify it resolves by new slug
    resolved = resolve_memory(paths, "new-name")
    assert resolved.id == mem.id


def test_rename_memory_duplicate_name_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    create_memory(paths, name="First")
    mem2 = create_memory(paths, name="Second")
    with pytest.raises(LaunchError, match="already exists with name"):
        rename_memory(paths, mem2.id, "First")


def test_delete_memory(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="ToDelete", body="bye")
    deleted = delete_memory(paths, mem.id)
    assert deleted.id == mem.id
    assert load_memories(paths) == []


def test_delete_memory_removes_file(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="ToDelete2", body="bye2")
    md_path = memory_markdown_path(paths, mem)
    assert md_path.exists()
    deleted = delete_memory(paths, mem.id)
    assert deleted.id == mem.id
    assert not md_path.exists()


def test_update_memory_tags_add_and_remove(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Tags", body="t", tags=("a", "b"))
    updated = update_memory_tags(paths, mem.id, add_tags=("c",), remove_tags=("a",))
    assert "a" not in updated.tags
    assert "b" in updated.tags
    assert "c" in updated.tags


def test_save_memories_removes_stale(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem1 = create_memory(paths, name="Keep", body="k")
    mem2 = create_memory(paths, name="Remove", body="r")
    # Save only mem1, which should cause mem2 file to be deleted
    save_memories(paths, [mem1])
    loaded = load_memories(paths)
    assert len(loaded) == 1
    assert loaded[0].id == mem1.id


def test_save_memories_unlink_failure(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem1 = create_memory(paths, name="Keep", body="k")
    mem2 = create_memory(paths, name="Stale", body="s")
    stale_path = memory_markdown_path(paths, mem2)
    stale_path.chmod(0o000)
    stale_parent = stale_path.parent
    stale_parent.chmod(0o500)
    try:
        with pytest.raises(LaunchError, match="Failed to delete memory file"):
            save_memories(paths, [mem1])
    finally:
        stale_parent.chmod(0o755)
        stale_path.chmod(0o644)


def test_load_memories_filename_mismatch(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="Mismatch", body="x")
    # Rename file so stem != memory id
    old = memory_markdown_path(paths, mem)
    new = old.with_name("wrong-id.md")
    old.rename(new)
    with pytest.raises(LaunchError, match="does not match"):
        load_memories(paths)


def test_load_memories_wrong_path_in_frontmatter(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="BadPath", body="x")
    from dataclasses import replace

    from taskledger.storage.frontmatter import write_markdown_front_matter
    bad = replace(mem, path="memories/wrong.md")
    md_path = memory_markdown_path(paths, mem)
    write_markdown_front_matter(md_path, {"file_version": MARKDOWN_FILE_VERSION, **bad.to_dict()}, "x")
    with pytest.raises(LaunchError, match="front matter path must be"):
        load_memories(paths)


def test_load_memories_missing_required_keys(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.memories_dir.mkdir(parents=True, exist_ok=True)
    md_path = paths.memories_dir / "mem-0001.md"
    md_path.write_text("---\nfile_version: v1\nid: mem-0001\n---\nbody\n")
    with pytest.raises(LaunchError, match="missing required keys"):
        load_memories(paths)


def test_load_memories_wrong_file_version(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    mem = create_memory(paths, name="VerCheck", body="x")
    from taskledger.storage.frontmatter import write_markdown_front_matter
    md_path = memory_markdown_path(paths, mem)
    bad_meta = {"file_version": "v99", **{k: v for k, v in mem.to_dict().items()}}
    write_markdown_front_matter(md_path, bad_meta, "x")
    with pytest.raises(LaunchError, match="Unsupported memory file_version"):
        load_memories(paths)
