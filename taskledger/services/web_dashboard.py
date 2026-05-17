from __future__ import annotations

import socket
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from taskledger.errors import LaunchError
from taskledger.services.html_reports import (
    HtmlReportOptions,
    HtmlSiteOptions,
    render_error_html,
    render_site_index_html,
    render_task_report_html,
)


@dataclass(slots=True, frozen=True)
class DashboardServerConfig:
    workspace_root: Path
    host: str = "127.0.0.1"
    port: int = 8765
    task_ref: str | None = None
    refresh_seconds: int | None = 2
    open_browser: bool = False


class _DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    workspace_root: Path
    default_task_ref: str | None
    refresh_seconds: int | None


@dataclass(slots=True)
class DashboardServerHandle:
    server: _DashboardHTTPServer
    host: str
    port: int
    url: str
    _serving: bool = False

    def serve_forever(self) -> None:
        self._serving = True
        try:
            self.server.serve_forever()
        finally:
            self._serving = False

    def close(self) -> None:
        if self._serving:
            self.server.shutdown()
        self.server.server_close()


def launch_dashboard_server(config: DashboardServerConfig) -> DashboardServerHandle:
    _validate_host(config.host)
    if config.port < 0 or config.port > 65535:
        raise LaunchError("taskledger serve requires --port between 0 and 65535.")
    if config.refresh_seconds is not None and config.refresh_seconds <= 0:
        raise LaunchError("taskledger serve requires --refresh-seconds greater than 0.")
    server = _create_server(config)
    host = config.host
    port = int(server.server_address[1])
    url = _server_url(host, port)
    handle = DashboardServerHandle(server=server, host=host, port=port, url=url)
    if config.open_browser:
        webbrowser.open(url)
    return handle


def serve_dashboard(config: DashboardServerConfig) -> None:
    handle = launch_dashboard_server(config)
    try:
        handle.serve_forever()
    finally:
        handle.close()


def _validate_host(host: str) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise LaunchError("taskledger serve only binds to localhost in the MVP.")


def _create_server(config: DashboardServerConfig) -> _DashboardHTTPServer:
    address_family = socket.AF_INET6 if ":" in config.host else socket.AF_INET

    class DashboardHTTPServer(_DashboardHTTPServer):
        pass

    DashboardHTTPServer.address_family = address_family
    server = DashboardHTTPServer((config.host, config.port), _DashboardRequestHandler)
    server.workspace_root = config.workspace_root
    server.default_task_ref = config.task_ref
    server.refresh_seconds = config.refresh_seconds
    return server


class _DashboardRequestHandler(BaseHTTPRequestHandler):
    server: _DashboardHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path in {"", "/"}:
                if self.server.default_task_ref:
                    self._send_html(
                        200,
                        self._render_task(self.server.default_task_ref),
                    )
                else:
                    self._send_html(200, self._render_index())
                return
            if parsed.path == "/active-task.html":
                self._send_html(200, self._render_task(None))
                return
            if parsed.path.startswith("/task/"):
                ref = unquote(parsed.path.removeprefix("/task/"))
                self._send_html(200, self._render_task(ref))
                return
            if parsed.path.startswith("/tasks/") and parsed.path.endswith(".html"):
                task_id = Path(parsed.path).stem
                self._send_html(200, self._render_task(task_id))
                return
            if parsed.path == "/healthz":
                self._send_text(200, "ok\n", content_type="text/plain; charset=utf-8")
                return
            self._send_html(404, render_error_html("Not found", parsed.path))
        except LaunchError as exc:
            status, _ = _status_for_launch_error(exc)
            self._send_html(
                status,
                render_error_html(
                    "Taskledger error",
                    str(exc),
                    refresh_seconds=self.server.refresh_seconds,
                ),
            )

    def do_POST(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_HEAD(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _method_not_allowed(self) -> None:
        self._send_html(
            405,
            render_error_html(
                "Method not allowed",
                "Only GET requests are allowed.",
                refresh_seconds=self.server.refresh_seconds,
            ),
        )

    def _render_index(self) -> str:
        payload = render_site_index_html(
            self.server.workspace_root,
            options=HtmlSiteOptions(refresh_seconds=self.server.refresh_seconds),
        )
        content = payload.get("content")
        if not isinstance(content, str):
            raise LaunchError("Site index HTML was not rendered as text.")
        return content

    def _render_task(self, ref: str | None) -> str:
        task_ref = ref or "active"
        payload = render_task_report_html(
            self.server.workspace_root,
            task_ref,
            options=HtmlReportOptions(
                refresh_seconds=self.server.refresh_seconds,
                mode="served",
            ),
        )
        content = payload.get("content")
        if not isinstance(content, str):
            raise LaunchError("Task HTML was not rendered as text.")
        return content

    def _send_text(self, status: int, text: str, *, content_type: str) -> None:
        body = text.encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except _CLIENT_DISCONNECT_ERRORS:
            return

    def _send_html(self, status: int, content: str) -> None:
        self._send_text(status, content, content_type="text/html; charset=utf-8")


def _server_url(host: str, port: int) -> str:
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"http://{host}:{port}/"


def _status_for_launch_error(exc: LaunchError) -> tuple[int, str]:
    message = str(exc)
    if "Task not found:" in message or "Active task" in message:
        return 404, "NotFound"
    return 400, "BadRequest"


_CLIENT_DISCONNECT_ERRORS = (
    BrokenPipeError,
    ConnectionAbortedError,
    ConnectionResetError,
)


__all__ = [
    "DashboardServerConfig",
    "DashboardServerHandle",
    "launch_dashboard_server",
    "serve_dashboard",
]
