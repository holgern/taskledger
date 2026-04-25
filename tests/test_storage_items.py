"""Tests for taskledger.storage.items."""
from __future__ import annotations

from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths
from taskledger.storage.frontmatter import (
    write_markdown_front_matter,
)
from taskledger.storage.items import (
    create_work_item,
    load_work_items,
    resolve_work_item,
    save_work_item,
    save_work_items,
    update_work_item,
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


def test_load_work_items_empty(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    assert load_work_items(paths) == []


def test_create_and_load_work_item(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(
        paths,
        slug="my-task",
        title="My Task",
        description="Do the thing",
        status="draft",
        stage="intake",
    )
    assert item.slug == "my-task"
    assert item.title == "My Task"
    assert item.status == "draft"
    assert item.stage == "intake"
    assert item.id.startswith("it-")

    loaded = load_work_items(paths)
    assert len(loaded) == 1
    assert loaded[0].id == item.id
    assert loaded[0].description == "Do the thing"


def test_create_work_item_invalid_status(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(LaunchError, match="Unsupported work item status"):
        create_work_item(paths, slug="x", title="X", description="x", status="bogus")


def test_create_work_item_invalid_stage(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(LaunchError, match="Unsupported work item stage"):
        create_work_item(paths, slug="x", title="X", description="x", stage="bogus")


def test_create_work_item_duplicate_slug(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    create_work_item(paths, slug="dup", title="First", description="a")
    with pytest.raises(LaunchError, match="already exists with slug"):
        create_work_item(paths, slug="dup", title="Second", description="b")


def test_resolve_work_item_by_id(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(paths, slug="resolve-id", title="Resolve", description="d")
    resolved = resolve_work_item(paths, item.id)
    assert resolved.id == item.id


def test_resolve_work_item_by_slug(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    create_work_item(paths, slug="resolve-slug", title="Resolve", description="d")
    resolved = resolve_work_item(paths, "resolve-slug")
    assert resolved.slug == "resolve-slug"


def test_resolve_work_item_by_title(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    create_work_item(paths, slug="res-title", title="Exact Title Match", description="d")
    resolved = resolve_work_item(paths, "Exact Title Match")
    assert resolved.title == "Exact Title Match"


def test_resolve_work_item_unknown_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(LaunchError, match="Unknown project work item"):
        resolve_work_item(paths, "no-such-item")


def test_save_work_item(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(
        paths, slug="save-test", title="Save", description="d",
        status="draft", stage="intake",
    )
    from dataclasses import replace
    updated = replace(item, title="Saved Title")
    saved = save_work_item(paths, updated)
    assert saved.title == "Saved Title"
    # Verify persistence
    loaded = load_work_items(paths)
    assert len(loaded) == 1
    assert loaded[0].title == "Saved Title"


def test_save_work_item_slug_change_conflict(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item1 = create_work_item(paths, slug="alpha", title="Alpha", description="a")
    item2 = create_work_item(paths, slug="beta", title="Beta", description="b")
    from dataclasses import replace
    # Try to rename item2 slug to "alpha"
    renamed = replace(item2, slug="alpha")
    with pytest.raises(LaunchError, match="already exists with slug"):
        save_work_item(paths, renamed)


def test_update_work_item(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(paths, slug="upd", title="Upd", description="d")
    from dataclasses import replace
    updated = replace(item, title="Updated Title", description="new desc")
    result = update_work_item(paths, item.id, updated)
    assert result.title == "Updated Title"


def test_update_work_item_id_change_raises(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(paths, slug="nochange", title="NC", description="d")
    from dataclasses import replace
    changed_id = replace(item, id="it-9999")
    with pytest.raises(LaunchError, match="id cannot be changed"):
        update_work_item(paths, item.id, changed_id)


def test_update_work_item_slug_conflict(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item1 = create_work_item(paths, slug="first", title="First", description="a")
    item2 = create_work_item(paths, slug="second", title="Second", description="b")
    from dataclasses import replace
    renamed = replace(item2, slug="first")
    with pytest.raises(LaunchError, match="already exists with slug"):
        update_work_item(paths, item2.id, renamed)


def test_save_work_items_removes_stale(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item1 = create_work_item(paths, slug="keep", title="Keep", description="k")
    item2 = create_work_item(paths, slug="stale", title="Stale", description="s")
    save_work_items(paths, [item1])
    loaded = load_work_items(paths)
    assert len(loaded) == 1
    assert loaded[0].id == item1.id


def test_load_work_items_missing_required_keys(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.items_dir.mkdir(parents=True, exist_ok=True)
    md_path = paths.items_dir / "it-0001.md"
    md_path.write_text("---\nfile_version: v1\nid: it-0001\n---\nbody\n")
    with pytest.raises(LaunchError, match="missing required keys"):
        load_work_items(paths)


def test_load_work_items_filename_mismatch(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(paths, slug="fm", title="FM", description="d")
    md_path = paths.items_dir / f"{item.id}.md"
    wrong = md_path.with_name("wrong-id.md")
    md_path.rename(wrong)
    with pytest.raises(LaunchError, match="does not match"):
        load_work_items(paths)


def test_load_work_items_wrong_file_version(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    item = create_work_item(paths, slug="fv", title="FV", description="d")
    from dataclasses import replace
    bad = replace(item, description="d")
    md_path = paths.items_dir / f"{item.id}.md"
    meta = {"file_version": "v99", **{k: v for k, v in item.to_dict().items() if k != "description"}}
    write_markdown_front_matter(md_path, meta, "d")
    with pytest.raises(LaunchError, match="Unsupported work item file_version"):
        load_work_items(paths)
