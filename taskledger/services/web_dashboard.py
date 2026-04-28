from __future__ import annotations

import hashlib
import json
import socket
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from taskledger.errors import LaunchError
from taskledger.services.serve_read_model import (
    serve_dashboard_snapshot,
    serve_project_summary,
    serve_task_events,
    serve_task_summaries,
)
from taskledger.storage.task_store import (
    resolve_task_or_active,
    resolve_v2_paths,
    task_dir,
)


@dataclass(slots=True, frozen=True)
class DashboardServerConfig:
    workspace_root: Path
    host: str = "127.0.0.1"
    port: int = 8765
    task_ref: str | None = None
    refresh_ms: int = 1000
    open_browser: bool = False


@dataclass(slots=True)
class CachedResponse:
    revision: str
    body: bytes
    content_type: str


class _DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    workspace_root: Path
    default_task_ref: str | None
    refresh_ms: int
    cache: dict[str, CachedResponse]


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
    #status {{
      font-size: 0.9rem;
      color: #555;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
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
    <div id="content">
      <section>
        <h2>Status</h2>
        <pre id="status">Waiting for first refresh.</pre>
      </section>
      <div id="panels"></div>
    </div>
  </main>
  <script>
    const refreshMs = {json.dumps(refresh_ms)};
    const defaultTaskRef = {_safe_script_literal(task_ref)};
    let selectedTaskRef = defaultTaskRef ?? "active";
    let refreshTimer = null;
    let refreshInFlight = false;
    let lastUpdatedText = "never";
    let renderedTasksRevision = null;
    let renderedTasksSelection = null;

    const endpointState = {{
      tasks: {{
        key: null,
        etag: null,
        payload: null,
        error: null,
        lastRequestedAt: 0,
      }},
      project: {{
        key: null,
        etag: null,
        payload: null,
        error: null,
        lastRequestedAt: 0,
      }},
      dashboard: {{
        key: null,
        etag: null,
        payload: null,
        error: null,
        lastRequestedAt: 0,
      }},
      events: {{
        key: null,
        etag: null,
        payload: null,
        error: null,
        lastRequestedAt: 0,
      }},
    }};

    function apiTaskRef() {{
      return selectedTaskRef === "active" ? "active" : selectedTaskRef;
    }}

    function endpointPath(name) {{
      if (name === "tasks") return "/api/tasks";
      if (name === "project") return "/api/project";
      const taskRef = encodeURIComponent(apiTaskRef());
      if (name === "dashboard") return "/api/dashboard?task=" + taskRef;
      return "/api/events?task=" + taskRef + "&limit=50";
    }}

    function endpointCadence(name) {{
      if (name === "tasks") return Math.max(refreshMs * 5, 5000);
      if (name === "project") return Math.max(refreshMs * 15, 15000);
      return refreshMs;
    }}

    async function getJson(name, path) {{
      const state = endpointState[name];
      if (state.key !== path) {{
        state.key = path;
        state.etag = null;
        state.payload = null;
        state.error = null;
      }}
      const headers = {{}};
      if (state.etag) {{
        headers["If-None-Match"] = state.etag;
      }}
      const response = await fetch(path, {{ headers }});
      if (response.status === 304 && state.payload) {{
        return state.payload;
      }}
      const payload = await response.json();
      if (!response.ok) {{
        throw new Error(payload?.error?.message || ("HTTP " + response.status));
      }}
      state.etag = response.headers.get("ETag");
      state.payload = payload;
      return payload;
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

    function setStatus(text) {{
      const node = document.getElementById("status");
      if (node) {{
        node.textContent = text;
      }}
    }}

    function endpointMessage(name, emptyText) {{
      const state = endpointState[name];
      if (state.payload) {{
        return null;
      }}
      if (state.error) {{
        return emptyText + "\\nError: " + state.error;
      }}
      return emptyText;
    }}

    function endpointOrFallback(name, emptyText) {{
      return endpointMessage(name, emptyText) || emptyText;
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
      const task = dash?.task || {{}};
      const active = project?.active_task || {{}};
      const lock = dash?.lock || null;
      return [
        "Workspace: " + (project?.workspace_root || "-"),
        "Project dir: " + (project?.project_dir || "-"),
        "Active task: " + (
          (active.slug || task.slug || "-") +
          " (" + (active.task_id || task.id || "-") + ")"
        ),
        "Stage: " + (task.status_stage || "-"),
        "Active stage: " + (task.active_stage || "none"),
        "Lock: " + (lock ? (lock.stage + " (" + lock.run_id + ")") : "none"),
        "Health: " + (project?.health || "unknown"),
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
      if (!questions) {{
        return endpointOrFallback("dashboard", "Loading questions...");
      }}
      const items = questions.items || [];
      const lines = [
        "Open: " + (questions.open || 0) + " / Total: " + (questions.total || 0),
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
      if (!todos) {{
        return endpointOrFallback("dashboard", "Loading todos...");
      }}
      const items = todos.items || [];
      const lines = [
        "Done: " + (todos.done || 0) + " / Total: " + (todos.total || 0),
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
      if (!runs) {{
        return endpointOrFallback("dashboard", "Loading runs...");
      }}
      if (runs.length === 0) return "No runs.";
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
      if (!changes) {{
        return endpointOrFallback("dashboard", "Loading changes...");
      }}
      if (changes.length === 0) return "No changes.";
      return changes.map((change) => {{
        return (
          change.change_id + "  " + change.path + "  (" + change.kind + ")\\n" +
          (change.summary || "")
        );
      }}).join("\\n\\n");
    }}

    function formatValidation(validation) {{
      if (!validation) {{
        return endpointOrFallback("dashboard", "Loading validation...");
      }}
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
      if (!events) {{
        return endpointOrFallback("events", "Loading events...");
      }}
      const items = events.items || [];
      if (items.length === 0) return "No events.";
      return items.map((event) => {{
        const actor = event.actor?.actor_name || event.actor?.actor_type || "unknown";
        return event.ts + "  " + event.event + "  " + actor;
      }}).join("\\n");
    }}

    function renderTasks() {{
      const tasksPayload = endpointState.tasks.payload;
      if (!tasksPayload) {{
        return;
      }}
      const currentTaskId = endpointState.dashboard.payload?.task?.id || null;
      const selectionKey = String(selectedTaskRef) + "|" + String(currentTaskId);
      if (
        tasksPayload.revision === renderedTasksRevision &&
        selectionKey === renderedTasksSelection
      ) {{
        return;
      }}
      renderedTasksRevision = tasksPayload.revision || null;
      renderedTasksSelection = selectionKey;
      const tasksNode = document.getElementById("tasks");
      tasksNode.replaceChildren();
      for (const task of tasksPayload.tasks || []) {{
        const button = document.createElement("button");
        button.textContent = formatTaskButton(task);
        button.dataset.active = String(
          task.id === selectedTaskRef ||
          task.slug === selectedTaskRef ||
          task.id === currentTaskId
        );
        button.addEventListener("click", () => {{
          selectedTaskRef = task.id;
          renderedTasksSelection = null;
          renderTasks();
          refreshSelection().catch(renderError);
        }});
        tasksNode.append(button);
      }}
    }}

    function renderPanels() {{
      const panels = document.getElementById("panels");
      const project = endpointState.project.payload;
      const dashboard = endpointState.dashboard.payload;
      const events = endpointState.events.payload;
      panels.replaceChildren();

      appendSection(
        panels,
        "Workspace",
        project || dashboard
          ? formatHeader(project, dashboard)
          : endpointOrFallback("project", "Loading project summary...")
      );
      appendSection(
        panels,
        "Next action",
        dashboard
          ? JSON.stringify(dashboard.next_action || {{}}, null, 2)
          : endpointOrFallback("dashboard", "Loading dashboard...")
      );
      appendSection(
        panels,
        "Plans",
        dashboard
          ? formatPlans(dashboard.plans || [])
          : endpointOrFallback("dashboard", "Loading plans...")
      );
      appendSection(panels, "Questions", formatQuestions(dashboard?.questions));
      appendSection(panels, "Todos", formatTodos(dashboard?.todos));
      appendSection(panels, "Runs", formatRuns(dashboard?.runs));
      appendSection(panels, "Changes", formatChanges(dashboard?.changes));
      appendSection(panels, "Validation", formatValidation(dashboard?.validation));
      appendSection(panels, "Events", formatEvents(events));
    }}

    function render() {{
      renderTasks();
      renderPanels();
      const errors = Object.entries(endpointState)
        .filter(([, state]) => Boolean(state.error))
        .map(([name, state]) => name + " error: " + state.error);
      const status = [
        refreshInFlight ? "Refreshing..." : "Idle",
        "Selected task: " + apiTaskRef(),
        "Last updated: " + lastUpdatedText,
      ].concat(errors);
      setStatus(status.join("\\n"));
    }}

    function shouldRefresh(name, now) {{
      const state = endpointState[name];
      const path = endpointPath(name);
      if (state.key !== path) {{
        return true;
      }}
      if (state.payload === null) {{
        return true;
      }}
      return (now - state.lastRequestedAt) >= endpointCadence(name);
    }}

    async function refreshEndpoint(name, now) {{
      const state = endpointState[name];
      state.lastRequestedAt = now;
      try {{
        await getJson(name, endpointPath(name));
        state.error = null;
      }} catch (error) {{
        state.error = String(error);
      }}
    }}

    async function refresh() {{
      if (refreshInFlight) {{
        return;
      }}
      refreshInFlight = true;
      render();
      try {{
        const now = Date.now();
        const work = [];
        for (const name of ["project", "tasks", "dashboard", "events"]) {{
          if (shouldRefresh(name, now)) {{
            work.push(refreshEndpoint(name, now));
          }}
        }}
        await Promise.allSettled(work);
        lastUpdatedText = new Date().toLocaleTimeString();
        render();
      }} finally {{
        refreshInFlight = false;
        render();
      }}
    }}

    async function refreshSelection() {{
      endpointState.dashboard.lastRequestedAt = 0;
      endpointState.events.lastRequestedAt = 0;
      endpointState.dashboard.etag = null;
      endpointState.events.etag = null;
      await refresh();
    }}

    function scheduleRefresh(delay = refreshMs) {{
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => {{
        refresh().catch(renderError).finally(() => scheduleRefresh());
      }}, delay);
    }}

    function renderError(error) {{
      setStatus("Error: " + String(error));
      renderPanels();
    }}

    refresh().catch(renderError).finally(() => scheduleRefresh());
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
    server.cache = {}
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
                revision = _storage_revision_for_project(self.server.workspace_root)
                self._send_cached_json(
                    200,
                    revision,
                    lambda: serve_project_summary(self.server.workspace_root),
                )
                return
            if parsed.path == "/api/tasks":
                revision = _storage_revision_for_tasks(self.server.workspace_root)
                self._send_cached_json(
                    200,
                    revision,
                    lambda: serve_task_summaries(self.server.workspace_root),
                )
                return
            if parsed.path == "/api/dashboard":
                task_ref = _task_ref_from_query(query, self.server.default_task_ref)
                revision = _storage_revision_for_dashboard(
                    self.server.workspace_root, task_ref
                )
                self._send_cached_json(
                    200,
                    revision,
                    lambda: serve_dashboard_snapshot(
                        self.server.workspace_root,
                        ref=task_ref,
                    ),
                )
                return
            if parsed.path == "/api/events":
                task_ref = _task_ref_from_query(query, self.server.default_task_ref)
                revision = _storage_revision_for_events(
                    self.server.workspace_root, task_ref
                )
                self._send_cached_json(
                    200,
                    revision,
                    lambda: serve_task_events(
                        self.server.workspace_root,
                        ref=task_ref,
                        limit=_limit_from_query(query),
                    ),
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

    def _send_cached_json(
        self,
        status: int,
        revision: str,
        payload_factory: Callable[[], dict[str, object]],
    ) -> None:
        if self.headers.get("If-None-Match") == revision:
            try:
                self.send_response(304)
                self.send_header("ETag", revision)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
            except _CLIENT_DISCONNECT_ERRORS:
                return
            return

        cache_key = f"{self.path}:{revision}"
        cached = self.server.cache.get(cache_key)
        if cached is None:
            payload = payload_factory()
            payload["revision"] = revision
            cached = CachedResponse(
                revision=revision,
                body=(json.dumps(payload, sort_keys=True).encode("utf-8") + b"\n"),
                content_type="application/json",
            )
            if len(self.server.cache) > 128:
                self.server.cache.clear()
            self.server.cache[cache_key] = cached

        try:
            self.send_response(status)
            self.send_header("Content-Type", cached.content_type)
            self.send_header("Content-Length", str(len(cached.body)))
            self.send_header("ETag", revision)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(cached.body)
        except _CLIENT_DISCONNECT_ERRORS:
            return

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


def _storage_revision_for_project(workspace_root: Path) -> str:
    paths = resolve_v2_paths(workspace_root)
    return _revision_for_paths(
        paths.project_dir,
        [paths.active_task_path, *sorted(paths.tasks_dir.glob("task-*/task.md"))],
    )


def _storage_revision_for_tasks(workspace_root: Path) -> str:
    paths = resolve_v2_paths(workspace_root)
    return _revision_for_paths(
        paths.project_dir,
        [
            *sorted(paths.tasks_dir.glob("task-*/task.md")),
            *sorted(paths.tasks_dir.glob("task-*/lock.yaml")),
        ],
    )


def _storage_revision_for_dashboard(
    workspace_root: Path,
    task_ref: str | None,
) -> str:
    task = resolve_task_or_active(workspace_root, task_ref)
    paths = resolve_v2_paths(workspace_root)
    bundle = task_dir(paths, task.id)
    return _revision_for_paths(
        paths.project_dir,
        [bundle / "lock.yaml", *sorted(bundle.rglob("*.md"))],
    )


def _storage_revision_for_events(
    workspace_root: Path,
    task_ref: str | None,
) -> str:
    resolve_task_or_active(workspace_root, task_ref)
    paths = resolve_v2_paths(workspace_root)
    return _revision_for_paths(
        paths.project_dir,
        sorted(paths.events_dir.glob("*.ndjson")),
    )


def _revision_for_paths(project_dir: Path, paths: list[Path]) -> str:
    parts: list[str] = []
    seen: set[Path] = set()
    for path in sorted(paths, key=lambda item: str(item)):
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            stat = path.stat()
            parts.append(
                f"{_relative_path(project_dir, path)}:{stat.st_mtime_ns}:{stat.st_size}"
            )
        else:
            parts.append(f"{_relative_path(project_dir, path)}:missing")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _relative_path(project_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


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
