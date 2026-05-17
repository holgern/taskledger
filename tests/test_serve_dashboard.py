from __future__ import annotations

import errno
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from taskledger.domain.models import ActiveTaskState
from taskledger.errors import LaunchError
from taskledger.services.tasks import create_task
from taskledger.services.web_dashboard import (
    DashboardServerConfig,
    DashboardServerHandle,
    launch_dashboard_server,
)
from taskledger.storage.task_store import (
    ensure_v2_layout,
    resolve_v2_paths,
    save_active_task_state,
    task_dir,
)
from tests.support.builders import create_done_task, init_workspace


def _skip_if_socket_forbidden(exc: OSError) -> None:
    if exc.errno in {errno.EPERM, errno.EACCES}:
        pytest.skip("Socket bind not permitted in this test environment.")
    raise exc


@contextmanager
def _running_server(
    workspace_root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    task_ref: str | None = None,
    refresh_seconds: int | None = 2,
) -> DashboardServerHandle:
    try:
        handle = launch_dashboard_server(
            DashboardServerConfig(
                workspace_root=workspace_root,
                host=host,
                port=port,
                task_ref=task_ref,
                refresh_seconds=refresh_seconds,
            )
        )
    except OSError as exc:
        _skip_if_socket_forbidden(exc)
        raise
    thread = threading.Thread(target=handle.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    try:
        yield handle
    finally:
        handle.close()
        thread.join(timeout=1)


def _request(
    handle: DashboardServerHandle,
    path: str,
    *,
    method: str = "GET",
) -> Request:
    return Request(f"{handle.url.rstrip('/')}{path}", method=method)


def _load_html(handle: DashboardServerHandle, path: str) -> str:
    with urlopen(_request(handle, path), timeout=5) as response:
        return response.read().decode("utf-8")


def _load_error(
    handle: DashboardServerHandle,
    path: str,
    *,
    method: str = "GET",
) -> int:
    with pytest.raises(HTTPError) as exc_info:
        urlopen(_request(handle, path, method=method), timeout=5)
    return exc_info.value.code


def test_serve_root_returns_html_index_without_task_ref(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    with _running_server(ws, task_ref=None) as handle:
        html = _load_html(handle, "/")
    assert "<!doctype html>" in html
    assert "Taskledger HTML reports" in html
    assert "<script" not in html.lower()


def test_serve_root_returns_task_html_with_task_ref(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_done_task(ws, allow_lint_errors=True)
    with _running_server(ws, task_ref=task_id) as handle:
        html = _load_html(handle, "/")
    assert "<!doctype html>" in html
    assert f"{task_id} —" in html
    assert 'id="summary"' in html


def test_serve_positional_task_ref_renders_requested_task(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    task = create_task(
        ws,
        title="Requested Task",
        slug="requested-task",
        description="x",
    )
    with _running_server(ws) as handle:
        html = _load_html(handle, f"/task/{task.id}")
    assert "Requested Task" in html


def test_serve_active_task_page_renders_active_task(tmp_path: Path) -> None:
    ensure_v2_layout(tmp_path)
    task = create_task(
        tmp_path,
        title="Active Task",
        slug="active-task",
        description="x",
    )
    save_active_task_state(tmp_path, ActiveTaskState(task_id=task.id))
    with _running_server(tmp_path) as handle:
        html = _load_html(handle, "/active-task.html")
    assert "Active Task" in html


def test_serve_refresh_seconds_sets_meta_refresh(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    with _running_server(ws, refresh_seconds=2) as handle:
        html = _load_html(handle, "/")
    assert '<meta http-equiv="refresh" content="2">' in html


def test_serve_rejects_non_get_requests(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    with _running_server(ws) as handle:
        status = _load_error(handle, "/", method="POST")
    assert status == 405


def test_serve_rejects_non_loopback_hosts(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    with pytest.raises(LaunchError, match="localhost"):
        launch_dashboard_server(
            DashboardServerConfig(workspace_root=ws, host="0.0.0.0", refresh_seconds=2)
        )


def test_serve_unknown_task_returns_404_html(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    with _running_server(ws) as handle:
        status = _load_error(handle, "/task/missing-task")
    assert status == 404


def test_serve_html_updates_after_storage_change_on_next_request(
    tmp_path: Path,
) -> None:
    ws = init_workspace(tmp_path)
    task = create_task(ws, title="Old Title", slug="change-me", description="x")
    with _running_server(ws, task_ref=task.id) as handle:
        first = _load_html(handle, "/")
        task_path = task_dir(resolve_v2_paths(ws), task.id) / "task.md"
        updated = task_path.read_text(encoding="utf-8").replace(
            "Old Title",
            "New Title",
        )
        task_path.write_text(updated, encoding="utf-8")
        second = _load_html(handle, "/")
    assert "Old Title" in first
    assert "New Title" in second
