from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.storage import ensure_project_exists, init_project_state
from taskledger.storage.frontmatter import (
    read_markdown_front_matter,
    write_markdown_front_matter,
)
from taskledger.storage.items import (
    create_work_item,
    load_work_items,
    save_work_items,
    update_work_item,
)
from taskledger.storage.memories import (
    create_memory,
    delete_memory,
    load_memories,
    rename_memory,
    save_memories,
    write_memory_body,
)


def test_init_project_state_creates_markdown_item_and_memory_dirs(
    tmp_path: Path,
) -> None:
    paths, _ = init_project_state(tmp_path)

    assert paths.memories_dir.is_dir()
    assert paths.items_dir.is_dir()
    assert not (paths.memories_dir / "index.json").exists()
    assert not (paths.items_dir / "index.json").exists()


@pytest.mark.parametrize(
    ("relative_path", "message"),
    [
        ("items/index.json", "Legacy item JSON storage is unsupported"),
        ("memories/index.json", "Legacy memory JSON storage is unsupported"),
    ],
)
def test_ensure_project_exists_rejects_legacy_item_memory_indexes(
    tmp_path: Path, relative_path: str, message: str
) -> None:
    paths, _ = init_project_state(tmp_path)
    legacy_index = paths.project_dir / relative_path
    legacy_index.write_text("[]\n", encoding="utf-8")

    with pytest.raises(LaunchError, match=message):
        ensure_project_exists(tmp_path)


def test_memory_create_and_load_round_trip_markdown(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)

    created = create_memory(paths, name="Parser Plan", body="Step 1\nStep 2")

    memory_path = paths.memories_dir / f"{created.id}.md"
    metadata, body = read_markdown_front_matter(memory_path)
    assert metadata["file_version"] == "v1"
    assert metadata["id"] == created.id
    assert metadata["path"] == f"memories/{created.id}.md"
    assert body == "Step 1\nStep 2"

    loaded = load_memories(paths)
    assert len(loaded) == 1
    assert loaded[0].id == created.id
    assert loaded[0].summary is not None
    assert loaded[0].content_hash is not None


def test_memory_write_empty_body_keeps_markdown_file(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    created = create_memory(paths, name="Body Reset", body="non-empty")

    updated = write_memory_body(paths, created.id, "")
    memory_path = paths.memories_dir / f"{created.id}.md"
    metadata, body = read_markdown_front_matter(memory_path)

    assert memory_path.exists()
    assert metadata["file_version"] == "v1"
    assert body == ""
    assert metadata["summary"] is None
    assert metadata["content_hash"] is None
    assert updated.summary is None
    assert updated.content_hash is None


def test_memory_rename_updates_front_matter_but_not_filename(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    created = create_memory(paths, name="Initial Name", body="abc")

    renamed = rename_memory(paths, created.id, "Renamed Memory")

    memory_path = paths.memories_dir / f"{created.id}.md"
    metadata, _ = read_markdown_front_matter(memory_path)
    assert renamed.id == created.id
    assert memory_path.exists()
    assert metadata["name"] == "Renamed Memory"
    assert metadata["slug"] == "renamed-memory"


def test_memory_delete_removes_markdown_file(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    created = create_memory(paths, name="Delete Me", body="bye")

    delete_memory(paths, created.id)

    assert not (paths.memories_dir / f"{created.id}.md").exists()


def test_memory_duplicate_slug_rejected(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    create_memory(paths, name="Coverage Plan", body="one")

    with pytest.raises(LaunchError, match="slug"):
        create_memory(paths, name="coverage-plan", body="two")


def test_memory_loader_rejects_malformed_front_matter(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    (paths.memories_dir / "mem-1.md").write_text("plain text", encoding="utf-8")

    with pytest.raises(LaunchError, match="front matter"):
        load_memories(paths)


def test_memory_loader_rejects_filename_and_id_mismatch(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    write_markdown_front_matter(
        paths.memories_dir / "mem-1.md",
        {
            "id": "mem-2",
            "file_version": "v1",
            "name": "Mismatch",
            "slug": "mismatch",
            "path": "memories/mem-2.md",
            "tags": [],
            "summary": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "source_run_id": None,
            "content_hash": None,
        },
        "",
    )

    with pytest.raises(LaunchError, match="filename stem"):
        load_memories(paths)


def test_memory_loader_rejects_path_mismatch(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    write_markdown_front_matter(
        paths.memories_dir / "mem-1.md",
        {
            "id": "mem-1",
            "file_version": "v1",
            "name": "Mismatch",
            "slug": "mismatch",
            "path": "memories/other.md",
            "tags": [],
            "summary": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "source_run_id": None,
            "content_hash": None,
        },
        "",
    )

    with pytest.raises(LaunchError, match="front matter path must be"):
        load_memories(paths)


def test_save_memories_preserves_existing_body_and_removes_stale_files(
    tmp_path: Path,
) -> None:
    paths, _ = init_project_state(tmp_path)
    memory_a = create_memory(paths, name="A", body="keep me")
    memory_b = create_memory(paths, name="B", body="delete me")

    save_memories(paths, [replace(memory_a, name="A Updated")])

    metadata, body = read_markdown_front_matter(
        paths.memories_dir / f"{memory_a.id}.md"
    )
    assert metadata["name"] == "A Updated"
    assert metadata["file_version"] == "v1"
    assert body == "keep me"
    assert not (paths.memories_dir / f"{memory_b.id}.md").exists()


def test_item_create_and_load_round_trip_uses_body_description(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)

    created = create_work_item(
        paths,
        slug="parser-fix",
        title="Parser Fix",
        description="Repair parser handling",
    )

    item_path = paths.items_dir / f"{created.id}.md"
    metadata, body = read_markdown_front_matter(item_path)
    assert metadata["file_version"] == "v1"
    assert metadata["id"] == created.id
    assert "description" not in metadata
    assert body == "Repair parser handling"

    loaded = load_work_items(paths)
    assert len(loaded) == 1
    assert loaded[0].description == "Repair parser handling"


def test_item_loader_prefers_body_over_front_matter_description(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    write_markdown_front_matter(
        paths.items_dir / "it-1.md",
        {
            "id": "it-1",
            "file_version": "v1",
            "slug": "body-canonical",
            "title": "Body Canonical",
            "description": "wrong source",
            "status": "draft",
            "stage": "intake",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        "body source",
    )

    loaded = load_work_items(paths)
    assert loaded[0].description == "body source"


def test_item_update_rewrites_same_file(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    created = create_work_item(
        paths,
        slug="update-me",
        title="Before",
        description="before text",
    )

    updated = update_work_item(
        paths,
        created.id,
        replace(created, title="After", description="after text"),
    )

    metadata, body = read_markdown_front_matter(paths.items_dir / f"{created.id}.md")
    assert metadata["file_version"] == "v1"
    assert metadata["title"] == "After"
    assert body == "after text"
    assert updated.id == created.id


def test_item_duplicate_slug_rejected(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    create_work_item(
        paths,
        slug="duplicate",
        title="One",
        description="first",
    )

    with pytest.raises(LaunchError, match="slug"):
        create_work_item(
            paths,
            slug="duplicate",
            title="Two",
            description="second",
        )


def test_item_loader_rejects_malformed_front_matter(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    (paths.items_dir / "it-1.md").write_text("plain text", encoding="utf-8")

    with pytest.raises(LaunchError, match="front matter"):
        load_work_items(paths)


def test_item_loader_rejects_filename_and_id_mismatch(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    write_markdown_front_matter(
        paths.items_dir / "it-1.md",
        {
            "id": "it-2",
            "file_version": "v1",
            "slug": "mismatch",
            "title": "Mismatch",
            "status": "draft",
            "stage": "intake",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        "text",
    )

    with pytest.raises(LaunchError, match="filename stem"):
        load_work_items(paths)


def test_save_work_items_removes_stale_files(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    item_a = create_work_item(paths, slug="a", title="A", description="a")
    item_b = create_work_item(paths, slug="b", title="B", description="b")

    save_work_items(paths, [replace(item_a, title="A2", description="a2")])

    metadata, body = read_markdown_front_matter(paths.items_dir / f"{item_a.id}.md")
    assert metadata["file_version"] == "v1"
    assert metadata["title"] == "A2"
    assert body == "a2"
    assert not (paths.items_dir / f"{item_b.id}.md").exists()


def test_memory_loader_rejects_unsupported_file_version(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    write_markdown_front_matter(
        paths.memories_dir / "mem-1.md",
        {
            "file_version": "v2",
            "id": "mem-1",
            "name": "Mismatch",
            "slug": "mismatch",
            "path": "memories/mem-1.md",
            "tags": [],
            "summary": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "source_run_id": None,
            "content_hash": None,
        },
        "",
    )

    with pytest.raises(LaunchError, match="Unsupported memory file_version"):
        load_memories(paths)


def test_item_loader_rejects_unsupported_file_version(tmp_path: Path) -> None:
    paths, _ = init_project_state(tmp_path)
    write_markdown_front_matter(
        paths.items_dir / "it-1.md",
        {
            "file_version": "v2",
            "id": "it-1",
            "slug": "mismatch",
            "title": "Mismatch",
            "status": "draft",
            "stage": "intake",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        "text",
    )

    with pytest.raises(LaunchError, match="Unsupported work item file_version"):
        load_work_items(paths)
