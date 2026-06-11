"""Performance tests: verify that hot-path commands read minimal Markdown files.

These tests count front-matter reads rather than measuring wall-clock time,
so they are deterministic and not flaky.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tests.support.builders import (
    create_approved_task,
    init_workspace,
)


def test_resolve_task_by_id_reads_one_file(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    ids = []
    for i in range(5):
        tid = create_approved_task(ws, title=f"Task {i}", slug=f"task-{i}")
        ids.append(tid)

    from taskledger.storage import task_store
    from taskledger.storage.task_store import resolve_task

    counter: Counter = Counter()
    original = task_store.read_markdown_front_matter

    def counted(path: Path) -> tuple:
        counter[path.name] += 1
        return original(path)

    with patch.object(task_store, "read_markdown_front_matter", counted):
        task = resolve_task(ws, ids[2])

    assert task.id == ids[2]
    task_md_reads = sum(v for k, v in counter.items() if k == "task.md")
    assert task_md_reads == 1, (
        f"Expected 1 task.md read, got {task_md_reads}: {counter}"
    )


def test_resolve_task_by_slug_reads_all(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    ids = []
    for i in range(5):
        tid = create_approved_task(ws, title=f"Task {i}", slug=f"unique-slug-{i}")
        ids.append(tid)

    from taskledger.storage import task_store
    from taskledger.storage.task_store import resolve_task

    counter: Counter = Counter()
    original = task_store.read_markdown_front_matter

    def counted(path: Path) -> tuple:
        counter[path.name] += 1
        return original(path)

    with patch.object(task_store, "read_markdown_front_matter", counted):
        task = resolve_task(ws, "unique-slug-3")

    assert task.id == ids[3]
    task_md_reads = sum(v for k, v in counter.items() if k == "task.md")
    assert task_md_reads == 5, f"Expected 5 for slug, got {task_md_reads}"


def test_ready_work_skip_next_action(
    tmp_path: Path,
) -> None:
    ws = init_workspace(tmp_path)
    create_approved_task(ws, title="A", slug="task-a")
    create_approved_task(ws, title="B", slug="task-b")

    from taskledger.services.ready_work import ready_work_items
    from taskledger.storage.task_store import list_tasks_by_visibility

    visible = list_tasks_by_visibility(ws, visibility="visible")

    with patch("taskledger.services.ready_work.next_action") as mock_na:
        items = ready_work_items(ws, visible, include_next_action=False)

    mock_na.assert_not_called()
    assert len(items) == 2
    for item in items:
        assert "next_action" not in item
        assert isinstance(item.get("next"), str)
        assert isinstance(item.get("reason"), str)


def test_next_event_id_does_not_load_events(tmp_path: Path) -> None:
    from taskledger.storage.events import next_event_id

    with patch("taskledger.storage.events.load_events") as mock_load:
        eid = next_event_id(tmp_path, "2026-06-11T12:00:00+00:00")

    mock_load.assert_not_called()
    assert eid.startswith("evt-")
    assert len(eid.split("-")[-1]) == 12


def test_monitor_uses_summaries_for_in_progress(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_approved_task(ws, title="Ready", slug="ready-task")

    from taskledger.services.monitor import monitor_snapshot

    snapshot = monitor_snapshot(ws)

    assert isinstance(snapshot, dict)
    assert snapshot["kind"] == "monitor_snapshot"
    assert isinstance(snapshot.get("in_progress"), list)
    assert isinstance(snapshot.get("ready"), list)


def test_save_task_updates_task_index(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    tid = create_approved_task(ws, title="Index check", slug="index-check")

    from taskledger.storage.task_index import _read_index
    from taskledger.storage.task_store import resolve_v2_paths

    paths = resolve_v2_paths(ws)
    index = _read_index(paths)
    assert index is not None
    entries = index.get("entries", [])
    matching = [e for e in entries if isinstance(e, dict) and e.get("id") == tid]
    assert len(matching) == 1
    assert matching[0]["title"] == "Index check"


def test_missing_task_index_triggers_rebuild(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    tid = create_approved_task(ws, title="Rebuild check", slug="rebuild-check")

    from taskledger.storage.task_index import (
        _task_index_path,
        list_task_summaries,
    )
    from taskledger.storage.task_store import resolve_v2_paths

    paths = resolve_v2_paths(ws)
    index_path = _task_index_path(paths)

    # Index should exist from write-through.
    assert index_path.exists()

    # Delete it.
    index_path.unlink()
    assert not index_path.exists()

    # list_task_summaries should rebuild automatically.
    summaries = list_task_summaries(paths, visibility="visible")
    assert any(s.id == tid for s in summaries)
    assert index_path.exists()
