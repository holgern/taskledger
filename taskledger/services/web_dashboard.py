from __future__ import annotations

import hashlib
import json
import socket
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from taskledger.api.project import project_status, project_status_summary
from taskledger.errors import LaunchError
from taskledger.services.dashboard import dashboard
from taskledger.services.tasks import list_events
from taskledger.storage.task_store import resolve_task_or_active


@dataclass(slots=True, frozen=True)
class DashboardServerConfig:
    workspace_root: Path
    host: str = "127.0.0.1"
    port: int = 8765
    task_ref: str | None = None
    refresh_ms: int = 1000
    open_browser: bool = False


class _DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    workspace_root: Path
    default_task_ref: str | None
    refresh_ms: int


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


def render_index_html(*, refresh_ms: int, task_ref: str | None) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Taskledger dashboard</title>
  <style>
    :root {{ color-scheme: light dark; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; }}
    main {{
      display: grid;
      grid-template-columns: 20rem minmax(0, 1fr);
      min-height: 100vh;
    }}
    aside {{ border-right: 1px solid #c9c9c9; padding: 1rem; }}
    #content {{ padding: 1rem; display: grid; gap: 1rem; }}
    section {{ border: 1px solid #c9c9c9; border-radius: 0.5rem; padding: 1rem; }}
    h1, h2 {{ margin: 0 0 0.75rem 0; }}
    pre {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }}
    button {{
      width: 100%;
      text-align: left;
      border: 1px solid #c9c9c9;
      border-radius: 0.375rem;
      padding: 0.5rem 0.75rem;
      background: transparent;
      cursor: pointer;
      margin-bottom: 0.5rem;
    }}
    button[data-active="true"] {{ border-color: #2563eb; }}
  </style>
</head>
<body>
  <main>
    <aside>
      <h1>Tasks</h1>
      <div id="tasks"></div>
    </aside>
    <div id="content"></div>
  </main>
  <script>
    const refreshMs = {json.dumps(refresh_ms)};
    const defaultTaskRef = {_safe_script_literal(task_ref)};
    let selectedTaskRef = defaultTaskRef ?? "active";

    async function getJson(path) {{
      const response = await fetch(path);
      const payload = await response.json();
      if (!response.ok) {{
        throw new Error(payload?.error?.message || ("HTTP " + response.status));
      }}
      return payload;
    }}

    function apiTaskRef() {{
      return selectedTaskRef === "active" ? "active" : selectedTaskRef;
    }}

    function appendSection(container, title, text) {{
      const section = document.createElement("section");
      const heading = document.createElement("h2");
      const pre = document.createElement("pre");
      heading.textContent = title;
      pre.textContent = text;
      section.append(heading, pre);
      container.append(section);
    }}

    function formatTaskButton(task) {{
      const title = task.title || task.slug || task.id;
      return (
        title + "\\n" + task.id + "  " +
        task.status_stage + " / " +
        (task.active_stage || "none")
      );
    }}

    function formatHeader(project, dash) {{
      const task = dash.task || {{}};
      const active = project.status?.active_task || {{}};
      const lock = dash.lock;
      return [
        "Workspace: " + (project.status?.workspace_root || "-"),
        "Project dir: " + (project.status?.project_dir || "-"),
        "Active task: " + (
          (active.slug || task.slug || "-") +
          " (" + (active.task_id || task.id || "-") + ")"
        ),
        "Stage: " + (task.status_stage || "-"),
        "Active stage: " + (task.active_stage || "none"),
        "Lock: " + (lock ? (lock.stage + " (" + lock.run_id + ")") : "none"),
        "Health: " + (project.status?.healthy ? "healthy" : "issues detected"),
      ].join("\\n");
    }}

    function formatPlans(plans) {{
      if (!plans || plans.length === 0) return "No plans.";
      return plans.map((plan) => {{
        const criteria = (plan.criteria || [])
          .map((item) => "- " + item.id + ": " + item.text)
          .join("\\n");
        const todos = (plan.todos || [])
          .map((item) => "- " + item.id + ": " + item.text)
          .join("\\n");
        const tests = (plan.test_commands || [])
          .map((item) => "- " + item)
          .join("\\n");
        const outputs = (plan.expected_outputs || [])
          .map((item) => "- " + item)
          .join("\\n");
        return [
          "v" + plan.plan_version + "  " + plan.status,
          "Goal: " + (plan.goal || "-"),
          criteria ? "Criteria:\\n" + criteria : "Criteria: none",
          todos ? "Todos:\\n" + todos : "Todos: none",
          tests ? "Tests:\\n" + tests : "Tests: none",
          outputs ? "Expected outputs:\\n" + outputs : "Expected outputs: none",
          plan.body || "",
        ].join("\\n");
      }}).join("\\n\\n");
    }}

    function formatQuestions(questions) {{
      const items = questions?.items || [];
      const lines = [
        "Open: " + (questions?.open || 0) +
          " / Total: " + (questions?.total || 0),
      ];
      if (items.length === 0) {{
        lines.push("No questions.");
      }} else {{
        for (const item of items) {{
          lines.push("- " + item.id + " [" + item.status + "] " + item.question);
        }}
      }}
      return lines.join("\\n");
    }}

    function formatTodos(todos) {{
      const items = todos?.items || [];
      const lines = [
        "Done: " + (todos?.done || 0) + " / Total: " + (todos?.total || 0),
      ];
      if (items.length === 0) {{
        lines.push("No todos.");
      }} else {{
        for (const item of items) {{
          lines.push(
            "- [" + (item.done ? "x" : " ") + "] " + item.id + " " + item.text
          );
        }}
      }}
      return lines.join("\\n");
    }}

    function formatRuns(runs) {{
      if (!runs || runs.length === 0) return "No runs.";
      return runs.map((run) => {{
        return [
          run.run_id + "  " + run.run_type + "  " + run.status +
            (run.result ? " [" + run.result + "]" : ""),
          "Started: " + (run.started_at || "-"),
          "Finished: " + (run.finished_at || "-"),
          "Summary: " + (run.summary || "-"),
        ].join("\\n");
      }}).join("\\n\\n");
    }}

    function formatChanges(changes) {{
      if (!changes || changes.length === 0) return "No changes.";
      return changes.map((change) => {{
        return (
          change.change_id + "  " + change.path + "  (" + change.kind + ")\\n" +
          (change.summary || "")
        );
      }}).join("\\n\\n");
    }}

    function formatValidation(validation) {{
      if (!validation) return "No validation status.";
      const criteria = (validation.criteria || []).map((item) => {{
        return "- " + item.id + " [" + item.latest_status + "] " + item.text;
      }}).join("\\n");
      const blockers = (validation.blockers || [])
        .map((item) => "- " + item.message)
        .join("\\n");
      return [
        "Run: " + (validation.run_id || "none"),
        "Can finish: " + (validation.can_finish_passed ? "yes" : "no"),
        criteria ? "Criteria:\\n" + criteria : "Criteria: none",
        blockers ? "Blockers:\\n" + blockers : "Blockers: none",
      ].join("\\n");
    }}

    function formatEvents(events) {{
      const items = events?.items || [];
      if (items.length === 0) return "No events.";
      return items.map((event) => {{
        const actor = event.actor?.actor_name || event.actor?.actor_type || "unknown";
        return event.ts + "  " + event.event + "  " + actor;
      }}).join("\\n");
    }}

    function render(tasksPayload, projectPayload, dashPayload, eventsPayload) {{
      const tasksNode = document.getElementById("tasks");
      const contentNode = document.getElementById("content");
      tasksNode.replaceChildren();
      contentNode.replaceChildren();

      for (const task of tasksPayload.tasks || []) {{
        const button = document.createElement("button");
        button.textContent = formatTaskButton(task);
        button.dataset.active = String(
          task.id === dashPayload.task?.id || task.slug === selectedTaskRef
        );
        button.addEventListener("click", () => {{
          selectedTaskRef = task.id;
          refresh().catch(renderError);
        }});
        tasksNode.append(button);
      }}

      appendSection(
        contentNode,
        "Workspace",
        formatHeader(projectPayload, dashPayload)
      );
      appendSection(
        contentNode,
        "Next action",
        JSON.stringify(dashPayload.next_action || {{}}, null, 2)
      );
      appendSection(contentNode, "Plans", formatPlans(dashPayload.plans || []));
      appendSection(contentNode, "Questions", formatQuestions(dashPayload.questions));
      appendSection(contentNode, "Todos", formatTodos(dashPayload.todos));
      appendSection(contentNode, "Runs", formatRuns(dashPayload.runs || []));
      appendSection(contentNode, "Changes", formatChanges(dashPayload.changes || []));
      appendSection(
        contentNode,
        "Validation",
        formatValidation(dashPayload.validation)
      );
      appendSection(contentNode, "Events", formatEvents(eventsPayload));
    }}

    function renderError(error) {{
      const contentNode = document.getElementById("content");
      contentNode.replaceChildren();
      appendSection(contentNode, "Dashboard error", String(error));
    }}

    async function refresh() {{
      const taskRef = encodeURIComponent(apiTaskRef());
      const [tasksPayload, projectPayload, dashPayload, eventsPayload] =
        await Promise.all([
          getJson("/api/tasks"),
          getJson("/api/project"),
          getJson("/api/dashboard?task=" + taskRef),
          getJson("/api/events?task=" + taskRef + "&limit=50"),
        ]);
      render(tasksPayload, projectPayload, dashPayload, eventsPayload);
    }}

    refresh().catch(renderError);
    setInterval(() => {{
      refresh().catch(renderError);
    }}, refreshMs);
  </script>
</body>
</html>
"""


def launch_dashboard_server(config: DashboardServerConfig) -> DashboardServerHandle:
    _validate_host(config.host)
    if config.port < 0 or config.port > 65535:
        raise LaunchError("taskledger serve requires --port between 0 and 65535.")
    if config.refresh_ms <= 0:
        raise LaunchError("taskledger serve requires --refresh-ms greater than 0.")
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
    server.refresh_ms = config.refresh_ms
    return server


class _DashboardRequestHandler(BaseHTTPRequestHandler):
    server: _DashboardHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self._send_text(
                    200,
                    render_index_html(
                        refresh_ms=self.server.refresh_ms,
                        task_ref=self.server.default_task_ref,
                    ),
                    content_type="text/html; charset=utf-8",
                )
                return
            if parsed.path == "/api/project":
                self._send_json(
                    200,
                    {
                        "kind": "project",
                        "status": project_status_summary(self.server.workspace_root),
                    },
                )
                return
            if parsed.path == "/api/tasks":
                project = project_status(self.server.workspace_root)
                raw_tasks = project.get("tasks", [])
                tasks = raw_tasks if isinstance(raw_tasks, list) else []
                self._send_json(
                    200,
                    {"kind": "tasks", "tasks": tasks},
                )
                return
            if parsed.path == "/api/dashboard":
                payload = dashboard(
                    self.server.workspace_root,
                    ref=_task_ref_from_query(query, self.server.default_task_ref),
                )
                payload["revision"] = _revision_for_payload(payload)
                self._send_json(200, payload)
                return
            if parsed.path == "/api/events":
                limit = _limit_from_query(query)
                task = resolve_task_or_active(
                    self.server.workspace_root,
                    _task_ref_from_query(query, self.server.default_task_ref),
                )
                events = [
                    item
                    for item in list_events(self.server.workspace_root)
                    if item.get("task_id") == task.id
                ]
                self._send_json(
                    200,
                    {
                        "kind": "events",
                        "task_id": task.id,
                        "items": events[-limit:],
                    },
                )
                return
            self._send_api_error(404, "NotFound", f"Unknown path: {parsed.path}")
        except LaunchError as exc:
            error_status, error_type = _status_for_launch_error(exc)
            self._send_api_error(error_status, error_type, str(exc))
        except ValueError as exc:
            self._send_api_error(400, "BadRequest", str(exc))
        except Exception as exc:  # noqa: BLE001
            self._send_api_error(500, "InternalError", str(exc))

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
        self._send_api_error(405, "MethodNotAllowed", "Only GET requests are allowed.")

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

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        self._send_text(
            status,
            json.dumps(payload, sort_keys=True) + "\n",
            content_type="application/json",
        )

    def _send_api_error(self, status: int, error_type: str, message: str) -> None:
        self._send_json(
            status,
            {
                "ok": False,
                "error": {
                    "type": error_type,
                    "message": message,
                },
            },
        )


def _task_ref_from_query(
    query: dict[str, list[str]],
    default_task_ref: str | None,
) -> str | None:
    raw = _first_query_value(query, "task")
    if raw is None or raw == "active":
        return default_task_ref
    return raw


def _limit_from_query(query: dict[str, list[str]]) -> int:
    raw = _first_query_value(query, "limit")
    if raw is None:
        return 50
    try:
        limit = int(raw)
    except ValueError as exc:
        raise ValueError("Invalid limit value.") from exc
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")
    return limit


def _first_query_value(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name, [])
    if not values:
        return None
    return values[0].strip() or None


def _revision_for_payload(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _safe_script_literal(value: str | None) -> str:
    encoded = json.dumps(value)
    return (
        encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )


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
    "render_index_html",
    "serve_dashboard",
]
