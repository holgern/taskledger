from __future__ import annotations

# ruff: noqa: E501
import hashlib
import json
import socket
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from textwrap import dedent
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
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>Taskledger dashboard</title>",
            _render_dashboard_css(),
            "</head>",
            _render_dashboard_body(),
            _render_dashboard_script(refresh_ms, task_ref),
            "</html>",
        ]
    )


def _render_dashboard_css() -> str:
    return dedent(
        """\
        <style>
          :root {
            color-scheme: light dark;
            --bg: #f6f7f9;
            --panel: #ffffff;
            --panel-muted: #f1f5f9;
            --panel-strong: #e8eef8;
            --text: #0f172a;
            --muted: #64748b;
            --border: #d7dde6;
            --accent: #2563eb;
            --accent-soft: rgba(37, 99, 235, 0.12);
            --success: #15803d;
            --warning: #b45309;
            --danger: #b91c1c;
            --radius: 14px;
            --shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
          }

          @media (prefers-color-scheme: dark) {
            :root {
              --bg: #0b1020;
              --panel: #111827;
              --panel-muted: #182235;
              --panel-strong: #1f2d44;
              --text: #e5e7eb;
              --muted: #9ca3af;
              --border: #263244;
              --accent-soft: rgba(96, 165, 250, 0.18);
              --shadow: none;
            }
          }

          * { box-sizing: border-box; }
          html, body { min-height: 100%; }
          body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.5;
          }
          button, input {
            font: inherit;
            color: inherit;
          }
          code, pre, .mono {
            font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
          }
          pre {
            margin: 0;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
          }
          button {
            border: none;
            background: none;
            padding: 0;
          }
          button:focus-visible,
          input:focus-visible,
          summary:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
          }
          .app-header {
            position: sticky;
            top: 0;
            z-index: 10;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border);
            background: color-mix(in srgb, var(--bg) 92%, transparent);
            backdrop-filter: blur(8px);
          }
          .eyebrow {
            margin: 0 0 0.35rem 0;
            color: var(--muted);
            font-size: 0.8rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .app-header h1 {
            margin: 0;
            font-size: 1.6rem;
          }
          .app-subtitle,
          .status-detail {
            margin: 0.35rem 0 0 0;
            color: var(--muted);
            max-width: 52rem;
          }
          .header-meta {
            display: grid;
            gap: 0.75rem;
            min-width: 16rem;
          }
          .meta-card,
          .card {
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--panel);
            box-shadow: var(--shadow);
          }
          .meta-card {
            padding: 0.75rem 0.9rem;
          }
          .meta-label {
            display: block;
            color: var(--muted);
            font-size: 0.8rem;
            margin-bottom: 0.25rem;
          }
          .dashboard-layout {
            display: grid;
            grid-template-columns: minmax(18rem, 22rem) minmax(0, 1fr) minmax(18rem, 22rem);
            gap: 1rem;
            padding: 1rem 1.25rem 1.5rem;
            align-items: start;
          }
          .sidebar-sticky,
          .rail-sticky {
            position: sticky;
            top: 6.75rem;
            display: grid;
            gap: 1rem;
          }
          .main-column,
          .hero-grid,
          .metric-grid,
          .section-stack,
          .rail-sticky {
            display: grid;
            gap: 1rem;
          }
          .main-column {
            min-width: 0;
          }
          .metric-grid {
            grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
          }
          .card {
            padding: 1rem;
            min-width: 0;
          }
          .muted-card {
            background: var(--panel-muted);
          }
          .card-header {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: flex-start;
            margin-bottom: 0.9rem;
          }
          .card-header h2,
          .card-header h3 {
            margin: 0;
            font-size: 1rem;
          }
          .hero-card {
            padding: 1.15rem;
          }
          .hero-title {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            align-items: center;
            margin-bottom: 0.6rem;
          }
          .hero-title h2 {
            margin: 0;
            font-size: 1.35rem;
          }
          .hero-meta,
          .mini-meta,
          .metric-value,
          .list-grid,
          .timeline {
            display: grid;
            gap: 0.65rem;
          }
          .hero-meta {
            grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
          }
          .meta-row {
            padding: 0.75rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--panel-muted);
          }
          .meta-row strong,
          .metric-number {
            display: block;
            font-size: 1.1rem;
            margin-top: 0.2rem;
          }
          .muted {
            color: var(--muted);
          }
          .badge-row,
          .filter-row,
          .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
          }
          .badge,
          .chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            font-size: 0.8rem;
            line-height: 1;
            padding: 0.38rem 0.65rem;
            border: 1px solid var(--border);
            background: var(--panel-muted);
            color: var(--text);
          }
          .chip {
            cursor: pointer;
          }
          .chip[data-active="true"],
          .task-card[data-active="true"] {
            border-color: var(--accent);
            background: var(--accent-soft);
          }
          .badge-success { color: var(--success); }
          .badge-warning { color: var(--warning); }
          .badge-danger { color: var(--danger); }
          .badge-info { color: var(--accent); }
          .badge-muted { color: var(--muted); }
          .search-stack {
            display: grid;
            gap: 0.65rem;
          }
          .search-stack label {
            font-size: 0.85rem;
            color: var(--muted);
          }
          .task-search {
            width: 100%;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--panel);
            padding: 0.8rem 0.9rem;
          }
          .task-list {
            display: grid;
            gap: 0.7rem;
          }
          .task-card {
            width: 100%;
            text-align: left;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--panel);
            box-shadow: var(--shadow);
            padding: 0.9rem;
            cursor: pointer;
          }
          .task-card:hover {
            border-color: var(--accent);
          }
          .task-title {
            margin: 0.4rem 0 0.3rem 0;
            font-size: 0.96rem;
            font-weight: 650;
          }
          .meta-line {
            color: var(--muted);
            font-size: 0.82rem;
          }
          .summary-line {
            margin-top: 0.55rem;
            color: var(--muted);
            font-size: 0.85rem;
          }
          .empty-state {
            border: 1px dashed var(--border);
            border-radius: 14px;
            padding: 0.9rem;
            color: var(--muted);
            background: var(--panel-muted);
          }
          .command-row {
            display: flex;
            gap: 0.65rem;
            align-items: center;
            flex-wrap: wrap;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--panel-muted);
            padding: 0.7rem 0.8rem;
          }
          .copy-button {
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--panel);
            padding: 0.45rem 0.7rem;
            cursor: pointer;
          }
          .progress-block {
            display: grid;
            gap: 0.4rem;
          }
          .progress-track {
            position: relative;
            height: 0.7rem;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: var(--panel-strong);
            overflow: hidden;
          }
          .progress-fill {
            position: absolute;
            inset: 0 auto 0 0;
            height: 100%;
            background: linear-gradient(90deg, var(--accent), #60a5fa);
            border-radius: inherit;
          }
          .criteria-grid,
          .change-grid {
            display: grid;
            gap: 0.75rem;
            grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
          }
          .item-card,
          .timeline-item {
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--panel-muted);
            padding: 0.85rem;
          }
          .todo-next {
            border-color: var(--accent);
            background: var(--accent-soft);
          }
          .item-title {
            display: flex;
            justify-content: space-between;
            gap: 0.65rem;
            align-items: flex-start;
            margin-bottom: 0.45rem;
          }
          .item-title strong {
            display: block;
          }
          ul.clean-list {
            margin: 0;
            padding-left: 1.1rem;
            display: grid;
            gap: 0.35rem;
          }
          details {
            border-top: 1px solid var(--border);
            margin-top: 0.75rem;
            padding-top: 0.75rem;
          }
          summary {
            cursor: pointer;
            color: var(--muted);
          }
          .section-subtitle {
            margin: -0.3rem 0 0.8rem 0;
            color: var(--muted);
          }
          .raw-payload details + details {
            margin-top: 0.75rem;
          }
          @media (max-width: 1200px) {
            .dashboard-layout {
              grid-template-columns: minmax(18rem, 22rem) minmax(0, 1fr);
            }
            .right-rail {
              grid-column: 1 / -1;
            }
            .rail-sticky {
              position: static;
              grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
            }
          }
          @media (max-width: 900px) {
            .app-header {
              position: static;
              flex-direction: column;
            }
            .header-meta {
              min-width: 0;
              width: 100%;
              grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
            }
            .dashboard-layout {
              grid-template-columns: 1fr;
            }
            .sidebar-sticky,
            .rail-sticky {
              position: static;
            }
          }
          @media (prefers-reduced-motion: reduce) {
            * {
              scroll-behavior: auto;
            }
          }
        </style>
        """
    ).strip()


def _render_dashboard_body() -> str:
    return dedent(
        """\
        <body>
          <header class="app-header">
            <div>
              <p class="eyebrow">Taskledger</p>
              <h1>Taskledger dashboard</h1>
              <p id="status-headline" class="app-subtitle">Waiting for first refresh.</p>
              <p id="status-detail" class="status-detail">The dashboard will load the selected task automatically.</p>
            </div>
            <div class="header-meta">
              <div class="meta-card">
                <span class="meta-label">Selected task</span>
                <strong id="selected-task-label">active</strong>
              </div>
              <div class="meta-card">
                <span class="meta-label">Last refresh</span>
                <strong id="last-updated-label">never</strong>
              </div>
            </div>
          </header>
          <div class="dashboard-layout">
            <aside aria-label="Tasks">
              <div class="sidebar-sticky">
                <section class="card muted-card">
                  <div class="search-stack">
                    <label for="task-search">Search tasks</label>
                    <input
                      id="task-search"
                      class="task-search"
                      type="search"
                      placeholder="Filter by title, task id, or slug"
                    >
                    <nav id="task-filters" class="filter-row" aria-label="Task filters"></nav>
                  </div>
                </section>
                <div id="tasks" class="task-list"></div>
              </div>
            </aside>
            <main class="main-column">
              <div id="hero-slot" class="hero-grid"></div>
              <section id="metric-grid" class="metric-grid" aria-label="Progress overview"></section>
              <div id="sections" class="section-stack"></div>
            </main>
            <aside class="right-rail" aria-label="Current work">
              <div id="rail-content" class="rail-sticky"></div>
            </aside>
          </div>
        """
    ).strip()


def _render_dashboard_script(refresh_ms: int, task_ref: str | None) -> str:
    script = dedent(
        """\
        <script>
          const refreshMs = __REFRESH_MS__;
          const defaultTaskRef = __DEFAULT_TASK_REF__;
          let selectedTaskRef = defaultTaskRef ?? "active";
          let refreshTimer = null;
          let refreshInFlight = false;
          let lastUpdatedText = "never";
          let taskSearchQuery = "";
          let taskStageFilter = "all";

          const STAGE_FILTERS = [
            { value: "all", label: "All" },
            { value: "active", label: "Active" },
            { value: "draft", label: "Draft" },
            { value: "review", label: "Review" },
            { value: "approved", label: "Approved" },
            { value: "implementation", label: "Implementing" },
            { value: "validation", label: "Validating" },
            { value: "failed", label: "Failed" },
            { value: "done", label: "Done" },
            { value: "cancelled", label: "Cancelled" },
          ];

          const endpointState = {
            tasks: { key: null, etag: null, payload: null, error: null, lastRequestedAt: 0 },
            project: { key: null, etag: null, payload: null, error: null, lastRequestedAt: 0 },
            dashboard: { key: null, etag: null, payload: null, error: null, lastRequestedAt: 0 },
            events: { key: null, etag: null, payload: null, error: null, lastRequestedAt: 0 },
          };

          function apiTaskRef() {
            return selectedTaskRef === "active" ? "active" : selectedTaskRef;
          }

          function endpointPath(name) {
            if (name === "tasks") return "/api/tasks";
            if (name === "project") return "/api/project";
            const taskRef = encodeURIComponent(apiTaskRef());
            if (name === "dashboard") return "/api/dashboard?task=" + taskRef;
            return "/api/events?task=" + taskRef + "&limit=50";
          }

          function endpointCadence(name) {
            if (name === "tasks") return Math.max(refreshMs * 5, 5000);
            if (name === "project") return Math.max(refreshMs * 15, 15000);
            return refreshMs;
          }

          async function getJson(name, path) {
            const state = endpointState[name];
            if (state.key !== path) {
              state.key = path;
              state.etag = null;
              state.payload = null;
              state.error = null;
            }
            const headers = {};
            if (state.etag) {
              headers["If-None-Match"] = state.etag;
            }
            const response = await fetch(path, { headers });
            if (response.status === 304 && state.payload) {
              return state.payload;
            }
            const payload = await response.json();
            if (!response.ok) {
              throw new Error(payload?.error?.message || ("HTTP " + response.status));
            }
            state.etag = response.headers.get("ETag");
            state.payload = payload;
            return payload;
          }

          function h(tag, attrs = {}, children = []) {
            const node = document.createElement(tag);
            for (const [key, value] of Object.entries(attrs || {})) {
              if (value === null || value === undefined || value === false) continue;
              if (key === "class") node.className = String(value);
              else if (key === "text") node.textContent = String(value);
              else if (key === "style") node.setAttribute("style", String(value));
              else if (key === "htmlFor") node.htmlFor = String(value);
              else if (key === "value") node.value = String(value);
              else if (key.startsWith("aria-") || key.startsWith("data-") || key === "role" || key === "type" || key === "placeholder" || key === "id") {
                node.setAttribute(key, String(value));
              } else {
                node[key] = value;
              }
            }
            const list = Array.isArray(children) ? children : [children];
            for (const child of list) {
              if (child === null || child === undefined) continue;
              node.append(child && child.nodeType ? child : document.createTextNode(String(child)));
            }
            return node;
          }

          function clearNode(node) {
            if (node) node.replaceChildren();
          }

          function emptyState(text) {
            return h("div", { class: "empty-state", text });
          }

          function titleCase(value) {
            return String(value || "").replace(/[_-]+/g, " ").replace(/\\b\\w/g, (letter) => letter.toUpperCase());
          }

          function formatTimestamp(value) {
            if (!value) return "Unknown";
            const parsed = new Date(value);
            if (Number.isNaN(parsed.getTime())) return String(value);
            return parsed.toLocaleString();
          }

          function toneForStage(task) {
            const stage = task?.status_stage;
            const activeStage = task?.active_stage;
            if (activeStage === "validation" || stage === "plan_review") return "warning";
            if (stage === "failed_validation") return "danger";
            if (stage === "done") return "success";
            if (stage === "cancelled") return "muted";
            if (activeStage || stage === "approved" || stage === "implemented") return "info";
            return "muted";
          }

          function toneForStatus(status) {
            if (status === "pass" || status === "done" || status === "finished" || status === "accepted") return "success";
            if (status === "fail" || status === "failed" || status === "failed_validation") return "danger";
            if (status === "warn" || status === "plan_review" || status === "running") return "warning";
            if (status === "not_run" || status === "open" || status === "draft" || status === "superseded") return "muted";
            return "info";
          }

          function badge(label, tone = "muted") {
            return h("span", { class: "badge badge-" + tone, text: label || "-" });
          }

          function jsonDetails(summary, payload) {
            const details = h("details");
            details.append(h("summary", { text: summary }), h("pre", { text: JSON.stringify(payload ?? {}, null, 2) }));
            return details;
          }

          function copyCommand(command) {
            if (!command) return;
            navigator.clipboard?.writeText(command).catch(() => undefined);
          }

          function commandRow(command) {
            if (!command) return emptyState("No command available.");
            const button = h("button", { class: "copy-button", type: "button", text: "Copy" });
            button.addEventListener("click", () => copyCommand(command));
            return h("div", { class: "command-row" }, [h("code", { text: command }), button]);
          }

          function progressBar(done, total) {
            const safeDone = Number(done || 0);
            const safeTotal = Number(total || 0);
            const pct = safeTotal > 0 ? Math.round((safeDone / safeTotal) * 100) : 0;
            const track = h(
              "div",
              {
                class: "progress-track",
                role: "progressbar",
                "aria-valuenow": pct,
                "aria-valuemin": 0,
                "aria-valuemax": 100,
                "aria-label": pct + "% complete",
              },
              [h("div", { class: "progress-fill", style: "width:" + pct + "%" })]
            );
            return h("div", { class: "progress-block" }, [
              h("strong", { text: safeDone + " / " + safeTotal }),
              track,
              h("span", { class: "muted", text: pct + "% complete" }),
            ]);
          }

          function endpointMessage(name, emptyText) {
            const state = endpointState[name];
            if (state.payload) return null;
            if (state.error) return emptyText + " Error: " + state.error;
            return emptyText;
          }

          function endpointOrFallback(name, emptyText) {
            return endpointMessage(name, emptyText) || emptyText;
          }

          function renderTaskFilters() {
            const container = document.getElementById("task-filters");
            clearNode(container);
            for (const filter of STAGE_FILTERS) {
              const button = h("button", {
                class: "chip",
                type: "button",
                text: filter.label,
                "data-active": String(taskStageFilter === filter.value),
              });
              button.addEventListener("click", () => {
                taskStageFilter = filter.value;
                renderTasks();
              });
              container.append(button);
            }
          }

          function taskMatchesFilter(task) {
            if (taskStageFilter === "all") return true;
            if (taskStageFilter === "active") return Boolean(task.active_stage);
            if (taskStageFilter === "review") return task.status_stage === "plan_review";
            if (taskStageFilter === "implementation") return task.active_stage === "implementation" || task.status_stage === "implemented";
            if (taskStageFilter === "validation") return task.active_stage === "validation" || task.status_stage === "validating";
            if (taskStageFilter === "failed") return task.status_stage === "failed_validation";
            return task.status_stage === taskStageFilter;
          }

          function sortedTasks(tasks) {
            return [...(tasks || [])].sort((left, right) => {
              const leftStamp = left.updated_at || left.created_at || "";
              const rightStamp = right.updated_at || right.created_at || "";
              if (leftStamp || rightStamp) {
                return String(rightStamp).localeCompare(String(leftStamp));
              }
              return String(right.id || "").localeCompare(String(left.id || ""));
            });
          }

          function renderTaskCard(task, currentTaskId) {
            const selected = Boolean(task.id === selectedTaskRef || task.slug === selectedTaskRef || task.id === currentTaskId);
            const button = h("button", { class: "task-card", type: "button", "data-active": String(selected) });
            button.setAttribute("aria-current", selected ? "true" : "false");
            button.addEventListener("click", () => {
              selectedTaskRef = task.id;
              render();
              refreshSelection().catch(renderError);
            });
            const idLabel = [task.id, task.slug].filter(Boolean).join(" · ");
            const planLabel = task.accepted_plan_version
              ? "plan v" + task.accepted_plan_version + " accepted"
              : task.latest_plan_version
                ? "plan v" + task.latest_plan_version + " proposed"
                : "no plan";
            const activeLabel = task.active_stage ? "active: " + task.active_stage : "active: none";
            button.append(
              h("div", { class: "badge-row" }, [
                badge(task.active_stage ? titleCase(task.active_stage) : titleCase(task.status_stage || "draft"), toneForStage(task)),
                task.priority ? badge("priority " + task.priority, "info") : null,
              ]),
              h("p", { class: "task-title", text: task.title || task.slug || task.id }),
              h("div", { class: "meta-line mono", text: idLabel || "-" }),
              h("div", { class: "meta-line", text: activeLabel }),
              h("div", { class: "meta-line", text: planLabel }),
              task.description_summary ? h("div", { class: "summary-line", text: task.description_summary }) : null
            );
            return button;
          }

          function renderTasks() {
            renderTaskFilters();
            const tasksNode = document.getElementById("tasks");
            clearNode(tasksNode);
            const tasksPayload = endpointState.tasks.payload;
            if (!tasksPayload) {
              tasksNode.append(emptyState(endpointOrFallback("tasks", "Loading tasks...")));
              return;
            }
            const currentTaskId = endpointState.dashboard.payload?.task?.id || null;
            const query = taskSearchQuery.trim().toLowerCase();
            const tasks = sortedTasks(tasksPayload.tasks).filter((task) => {
              const haystack = [task.title, task.slug, task.id].join(" ").toLowerCase();
              return (!query || haystack.includes(query)) && taskMatchesFilter(task);
            });
            if (tasks.length === 0) {
              tasksNode.append(emptyState("No tasks match the current search or filter."));
              return;
            }
            for (const task of tasks) {
              tasksNode.append(renderTaskCard(task, currentTaskId));
            }
          }

          function renderHero(project, dashboard) {
            const slot = document.getElementById("hero-slot");
            clearNode(slot);
            if (!dashboard) {
              slot.append(emptyState(endpointOrFallback("dashboard", "Loading dashboard summary...")));
              return;
            }
            const task = dashboard.task || {};
            const lock = dashboard.lock;
            const activeTask = project?.active_task || {};
            const hero = h("section", { class: "card hero-card active-task-hero" });
            hero.append(
              h("div", { class: "hero-title" }, [
                h("h2", { text: task.title || task.slug || task.id || "Active task" }),
                badge(task.status_stage || "unknown", toneForStage(task)),
                task.active_stage ? badge("active " + task.active_stage, "info") : badge("no active lock", "muted"),
              ]),
              h("p", { class: "section-subtitle", text: task.description_summary || "Human-focused read-only review of the selected task." }),
              h("div", { class: "hero-meta" }, [
                h("div", { class: "meta-row" }, [h("span", { class: "muted", text: "Task reference" }), h("strong", { class: "mono", text: [task.id, task.slug].filter(Boolean).join(" · ") || "-" })]),
                h("div", { class: "meta-row" }, [h("span", { class: "muted", text: "Lock state" }), h("strong", { text: lock ? lock.stage + " · " + lock.run_id : "No active lock" })]),
                h("div", { class: "meta-row" }, [h("span", { class: "muted", text: "Plan status" }), h("strong", { text: dashboard.plan ? "v" + dashboard.plan.version + " · " + dashboard.plan.status : "No plan proposed" })]),
                h("div", { class: "meta-row" }, [h("span", { class: "muted", text: "Project focus" }), h("strong", { text: activeTask.task_id ? (activeTask.slug || activeTask.task_id) + " · " + (project?.health || "not_checked") : project?.health || "not_checked" })]),
              ]),
              h("div", { class: "pill-row" }, [
                task.owner ? badge("owner " + task.owner, "info") : null,
                ...(task.labels || []).map((label) => badge(label, "muted")),
                task.created_at ? badge("created " + formatTimestamp(task.created_at), "muted") : null,
                task.updated_at ? badge("updated " + formatTimestamp(task.updated_at), "muted") : null,
              ])
            );
            slot.append(hero);
          }

          function renderMetrics(dashboard, events) {
            const grid = document.getElementById("metric-grid");
            clearNode(grid);
            if (!dashboard) {
              grid.append(emptyState(endpointOrFallback("dashboard", "Loading progress overview...")));
              return;
            }
            const validationCriteria = dashboard.validation?.criteria || [];
            const passedValidation = validationCriteria.filter((item) => item.satisfied).length;
            const cards = [
              { title: "Todos", detail: (dashboard.todos?.done || 0) + " complete of " + (dashboard.todos?.total || 0), body: progressBar(dashboard.todos?.done || 0, dashboard.todos?.total || 0) },
              { title: "Questions", detail: (dashboard.questions?.open || 0) + " open of " + (dashboard.questions?.total || 0), body: progressBar((dashboard.questions?.total || 0) - (dashboard.questions?.open || 0), dashboard.questions?.total || 0) },
              { title: "Validation", detail: passedValidation + " satisfied of " + validationCriteria.length, body: progressBar(passedValidation, validationCriteria.length) },
              { title: "Plan", detail: dashboard.plan ? "v" + dashboard.plan.version + " · " + dashboard.plan.status : "No plan", body: h("div", { class: "metric-value" }, [badge(dashboard.plan ? dashboard.plan.status : "none", toneForStatus(dashboard.plan?.status || "none"))]) },
              { title: "Runs", detail: (dashboard.runs || []).length + " recorded", body: h("div", { class: "metric-value" }, [h("strong", { class: "metric-number", text: dashboard.runs?.[0] ? dashboard.runs[0].run_id + " · " + dashboard.runs[0].status : "No runs" })]) },
              { title: "Events", detail: (events?.items || []).length + " recent entries", body: h("div", { class: "metric-value" }, [h("strong", { class: "metric-number", text: String((events?.items || []).length) }), h("span", { class: "muted", text: "Recent activity tail" })]) },
            ];
            for (const metric of cards) {
              grid.append(h("section", { class: "card" }, [h("div", { class: "card-header" }, [h("h2", { text: metric.title }), h("span", { class: "muted", text: metric.detail })]), metric.body]));
            }
          }

          function appendCard(container, title, children, className = "") {
            const section = h("section", { class: ("card " + className).trim() });
            section.append(h("div", { class: "card-header" }, [h("h2", { text: title })]));
            const list = Array.isArray(children) ? children : [children];
            for (const child of list) {
              if (child) section.append(child);
            }
            container.append(section);
          }

          function renderOverview(project, dashboard) {
            if (!project && !dashboard) return emptyState(endpointOrFallback("project", "Loading workspace summary..."));
            return h("div", { class: "list-grid" }, [
              h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: "Workspace" })]), h("div", { class: "mini-meta" }, [h("span", { class: "muted", text: "Workspace root" }), h("code", { text: project?.workspace_root || "-" }), h("span", { class: "muted", text: "Project dir" }), h("code", { text: project?.project_dir || "-" })])]),
              h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: "Selected task state" })]), h("div", { class: "mini-meta" }, [h("span", { class: "muted", text: "Stage" }), h("span", { text: dashboard?.task?.status_stage || "-" }), h("span", { class: "muted", text: "Active stage" }), h("span", { text: dashboard?.task?.active_stage || "none" }), h("span", { class: "muted", text: "Health" }), h("span", { text: project?.health || "unknown" })])]),
            ]);
          }

          function renderNextAction(dashboard) {
            const nextAction = dashboard?.next_action;
            if (!nextAction) return emptyState(endpointOrFallback("dashboard", "Loading next action..."));
            const task = dashboard?.task || {};
            const blockers = nextAction.blocking || [];
            const nextItem = nextAction.next_item;
            const todoProgress = nextAction.progress?.todos || {};
            const card = h("section", { class: "card next-action-card" });
            card.append(h("div", { class: "card-header" }, [h("h2", { text: "Do next" }), badge(nextAction.action || "none", toneForStatus(nextAction.action || "none"))]), h("p", { class: "section-subtitle", text: nextAction.reason || "No next action available." }));
            card.append(h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: task.title || task.slug || "Selected task" }), task.id ? h("code", { text: task.id }) : null]), h("div", { class: "mini-meta" }, [h("span", { class: "muted", text: "Stage" }), h("span", { text: task.status_stage || "-" }), h("span", { class: "muted", text: "Active" }), h("span", { text: task.active_stage || "none" })])]));
            if (nextAction.next_command) {
              card.append(h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: "Inspect" })]), commandRow(nextAction.next_command)]));
            }
            if (nextItem) {
              card.append(h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: nextItem.id || "Next item" }), nextItem.kind ? badge(nextItem.kind, "info") : null]), nextItem.text ? h("p", { text: nextItem.text }) : null, nextItem.validation_hint ? h("div", { class: "mini-meta" }, [h("span", { class: "muted", text: "Validation" })]) : null, nextItem.validation_hint ? commandRow(nextItem.validation_hint) : null, nextItem.done_command_hint ? h("div", { class: "mini-meta" }, [h("span", { class: "muted", text: "When done" })]) : null, nextItem.done_command_hint ? commandRow(nextItem.done_command_hint) : null]));
            }
            if (Object.keys(todoProgress).length > 0) {
              card.append(h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: "Todo progress" })]), h("p", { text: String(todoProgress.done || 0) + "/" + String(todoProgress.total || 0) + " done" })]));
            }
            if (blockers.length > 0) {
              card.append(h("div", { class: "list-grid" }, [h("h3", { text: "Blockers" }), h("ul", { class: "clean-list" }, blockers.map((blocker) => h("li", { text: blocker.message || blocker.kind || "Blocking issue" }))) ]));
            }
            return card;
          }

          function renderQuestionsSection(questions) {
            if (!questions) return emptyState(endpointOrFallback("dashboard", "Loading questions..."));
            if (!questions.items || questions.items.length === 0) return h("p", { class: "section-subtitle", text: "No planning questions are recorded." });
            return h("div", { class: "list-grid" }, questions.items.map((item) => h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: item.question || item.text || item.id }), badge(item.status || "open", toneForStatus(item.status || "open"))]), h("code", { text: item.id || "-" }), item.answer ? h("p", { text: item.answer }) : null])));
          }

          function renderPlanSection(plans) {
            if (!plans || plans.length === 0) return emptyState("No plans have been proposed yet.");
            const latest = plans[plans.length - 1];
            const body = h("div", { class: "list-grid" }, [h("p", { class: "section-subtitle", text: "Latest plan v" + latest.plan_version + " · " + (latest.status || "unknown") })]);
            if (latest.goal) body.append(h("p", { text: latest.goal }));
            if (latest.criteria?.length) {
              body.append(h("div", { class: "criteria-grid" }, latest.criteria.map((criterion) => h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: criterion.text || criterion.id }), criterion.id ? h("code", { text: criterion.id }) : null]), badge(criterion.mandatory === false ? "optional" : "mandatory", criterion.mandatory === false ? "muted" : "info")]))));
            }
            if (latest.todos?.length) {
              body.append(h("div", { class: "list-grid" }, latest.todos.map((todo) => h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: todo.text || todo.id }), todo.id ? h("code", { text: todo.id }) : null]), todo.validation_hint ? commandRow(todo.validation_hint) : null]))));
            }
            if (latest.test_commands?.length) {
              body.append(h("div", { class: "list-grid" }, [h("h3", { text: "Test commands" }), ...latest.test_commands.map((command) => commandRow(command))]));
            }
            if (latest.expected_outputs?.length) {
              body.append(h("ul", { class: "clean-list" }, latest.expected_outputs.map((item) => h("li", { text: item }))));
            }
            if (latest.body) body.append(jsonDetails("Expanded plan body", latest.body));
            if (plans.length > 1) {
              const details = h("details");
              details.append(h("summary", { text: "Previous versions" }), ...plans.slice(0, -1).reverse().map((plan) => h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: "v" + plan.plan_version }), badge(plan.status || "unknown", toneForStatus(plan.status || "unknown"))]), plan.goal ? h("p", { text: plan.goal }) : null, plan.body ? h("pre", { text: plan.body }) : null])));
              body.append(details);
            }
            return body;
          }

          function renderTodosSection(todos, nextAction) {
            if (!todos) return emptyState(endpointOrFallback("dashboard", "Loading todos..."));
            const highlightedTodoId = nextAction?.next_item?.kind === "todo" ? nextAction.next_item.id : null;
            const items = [...(todos.items || [])].sort((left, right) => Number(Boolean(left.done)) - Number(Boolean(right.done)));
            const todoCards = items.map((todo) => {
              const done = Boolean(todo.done || todo.status === "done");
              const card = h("div", { class: "item-card" + (todo.id === highlightedTodoId ? " todo-next" : "") }, [h("div", { class: "item-title" }, [h("strong", { text: todo.text || todo.id }), badge(done ? "done" : todo.status || "open", toneForStatus(done ? "done" : todo.status || "open"))]), h("code", { text: todo.id || "-" })]);
              const lines = [];
              if (todo.evidence) lines.push("Evidence: " + todo.evidence);
              if (todo.source) lines.push("Source: " + todo.source);
              if (todo.active_at) lines.push("Active at: " + todo.active_at);
              if (lines.length > 0) {
                const details = h("details");
                details.append(h("summary", { text: "Details" }), h("ul", { class: "clean-list" }, lines.map((line) => h("li", { text: line }))));
                card.append(details);
              }
              return card;
            });
            return h("div", { class: "list-grid" }, [
              h("p", { class: "section-subtitle", text: (todos.done || 0) + " done of " + (todos.total || 0) + " total" }),
              progressBar(todos.done || 0, todos.total || 0),
              items.length === 0 ? emptyState("No todos are recorded.") : h("div", { class: "list-grid" }, todoCards),
            ]);
          }

          function renderValidationSection(validation) {
            if (!validation) return emptyState(endpointOrFallback("dashboard", "Loading validation..."));
            const parts = [h("p", { class: "section-subtitle", text: validation.run_id ? "Validation run " + validation.run_id + " · " + (validation.can_finish_passed ? "ready to finish" : "checks remain") : "No validation run recorded" })];
            if ((validation.blockers || []).length > 0) {
              parts.push(h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: "Blockers" })]), h("ul", { class: "clean-list" }, validation.blockers.map((blocker) => h("li", { text: blocker.message || blocker.ref || blocker.kind || "Blocking issue" }))) ]));
            }
            parts.push((validation.criteria || []).length === 0 ? emptyState("No validation criteria were found.") : h("div", { class: "criteria-grid" }, validation.criteria.map((criterion) => {
              const card = h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: criterion.text || criterion.id }), badge(criterion.latest_status || "not_run", toneForStatus(criterion.latest_status || "not_run"))]), h("code", { text: criterion.id || "-" }), criterion.has_waiver ? badge("waived", "warning") : null, criterion.evidence?.length ? h("ul", { class: "clean-list" }, criterion.evidence.map((item) => h("li", { text: item }))) : h("p", { class: "muted", text: "No evidence recorded." })]);
              if (criterion.history?.length || criterion.blockers?.length) {
                const details = h("details");
                details.append(h("summary", { text: "History and blockers" }), criterion.history?.length ? h("ul", { class: "clean-list" }, criterion.history.map((item) => h("li", { text: (item.check_id || "check") + " · " + (item.status || "unknown") }))) : null, criterion.blockers?.length ? h("ul", { class: "clean-list" }, criterion.blockers.map((item) => h("li", { text: item.message || item.kind || "blocker" }))) : null);
                card.append(details);
              }
              return card;
            })));
            return h("div", { class: "list-grid" }, parts);
          }

          function renderRunsSection(runs) {
            if (!runs) return emptyState(endpointOrFallback("dashboard", "Loading runs..."));
            if (runs.length === 0) return emptyState("No implementation or validation runs are recorded.");
            return h("div", { class: "timeline" }, runs.map((run) => {
              const card = h("div", { class: "timeline-item" }, [h("div", { class: "item-title" }, [h("strong", { text: run.run_id + " · " + titleCase(run.run_type || "run") }), badge(run.result || run.status || "unknown", toneForStatus(run.result || run.status || "unknown"))]), h("p", { text: run.summary || "No summary recorded." }), h("div", { class: "mini-meta" }, [h("span", { class: "muted", text: "Started" }), h("span", { text: formatTimestamp(run.started_at) }), h("span", { class: "muted", text: "Finished" }), h("span", { text: run.finished_at ? formatTimestamp(run.finished_at) : "In progress" })])]);
              card.append(jsonDetails("Run details", run));
              return card;
            }));
          }

          function renderChangesSection(changes) {
            if (!changes) return emptyState(endpointOrFallback("dashboard", "Loading changes..."));
            if (changes.length === 0) return emptyState("No implementation changes are recorded.");
            return h("div", { class: "change-grid" }, changes.map((change) => {
              const card = h("div", { class: "item-card" }, [h("div", { class: "item-title" }, [h("strong", { text: change.summary || change.path || change.change_id }), badge(change.kind || "change", "info")]), h("code", { text: change.path || change.change_id || "-" })]);
              card.append(jsonDetails("Change metadata", change));
              return card;
            }));
          }

          function renderEventsSection(events) {
            if (!events) return emptyState(endpointOrFallback("events", "Loading events..."));
            if (!events.items || events.items.length === 0) return emptyState("No recent events are available.");
            return h("div", { class: "timeline" }, events.items.map((event) => {
              const actor = event.actor?.actor_name || event.actor?.actor_type || "unknown";
              const card = h("div", { class: "timeline-item" }, [h("div", { class: "item-title" }, [h("strong", { text: event.event || "event" }), h("span", { class: "muted mono", text: formatTimestamp(event.ts) })]), h("p", { text: actor })]);
              card.append(jsonDetails("Event payload", event));
              return card;
            }));
          }

          function renderRawSection(project, dashboard, events) {
            const card = h("section", { class: "card raw-payload" });
            card.append(h("div", { class: "card-header" }, [h("h2", { text: "Raw payload" })]), h("p", { class: "section-subtitle", text: "Debug payloads stay available without dominating the main dashboard." }), jsonDetails("Project payload", project || {}), jsonDetails("Dashboard payload", dashboard || {}), jsonDetails("Events payload", events || {}));
            return card;
          }

          function renderSections() {
            const project = endpointState.project.payload;
            const dashboard = endpointState.dashboard.payload;
            const events = endpointState.events.payload;
            renderHero(project, dashboard);
            renderMetrics(dashboard, events);
            const rail = document.getElementById("rail-content");
            clearNode(rail);
            rail.append(renderNextAction(dashboard));
            const sections = document.getElementById("sections");
            clearNode(sections);
            appendCard(sections, "Overview", renderOverview(project, dashboard));
            appendCard(sections, "Plan", renderPlanSection(dashboard?.plans));
            appendCard(sections, "Questions", renderQuestionsSection(dashboard?.questions));
            appendCard(sections, "Todos", renderTodosSection(dashboard?.todos, dashboard?.next_action));
            appendCard(sections, "Validation", renderValidationSection(dashboard?.validation));
            appendCard(sections, "Runs", renderRunsSection(dashboard?.runs));
            appendCard(sections, "Changes", renderChangesSection(dashboard?.changes));
            appendCard(sections, "Events", renderEventsSection(events));
            sections.append(renderRawSection(project, dashboard, events));
          }

          function setStatus() {
            const errors = Object.entries(endpointState).filter(([, state]) => Boolean(state.error)).map(([name, state]) => name + " error: " + state.error);
            const headline = document.getElementById("status-headline");
            const detail = document.getElementById("status-detail");
            const selected = document.getElementById("selected-task-label");
            const updated = document.getElementById("last-updated-label");
            if (headline) {
              headline.textContent = refreshInFlight ? "Refreshing dashboard data..." : "Showing a read-only review of the selected task.";
            }
            if (detail) {
              detail.textContent = errors.length > 0 ? errors.join(" · ") : "Polling dashboard and events every " + refreshMs + "ms with slower project and task refresh cadences.";
            }
            if (selected) {
              selected.textContent = endpointState.dashboard.payload?.task?.slug || apiTaskRef();
            }
            if (updated) {
              updated.textContent = lastUpdatedText;
            }
          }

          function render() {
            renderTasks();
            renderSections();
            setStatus();
          }

          function shouldRefresh(name, now) {
            const state = endpointState[name];
            const path = endpointPath(name);
            if (state.key !== path) return true;
            if (state.payload === null) return true;
            return (now - state.lastRequestedAt) >= endpointCadence(name);
          }

          async function refreshEndpoint(name, now) {
            const state = endpointState[name];
            state.lastRequestedAt = now;
            try {
              await getJson(name, endpointPath(name));
              state.error = null;
            } catch (error) {
              state.error = String(error);
            }
          }

          async function refresh() {
            if (refreshInFlight) return;
            refreshInFlight = true;
            render();
            try {
              const now = Date.now();
              const work = [];
              for (const name of ["project", "tasks", "dashboard", "events"]) {
                if (shouldRefresh(name, now)) {
                  work.push(refreshEndpoint(name, now));
                }
              }
              await Promise.allSettled(work);
              lastUpdatedText = new Date().toLocaleTimeString();
              render();
            } finally {
              refreshInFlight = false;
              render();
            }
          }

          async function refreshSelection() {
            endpointState.dashboard.lastRequestedAt = 0;
            endpointState.events.lastRequestedAt = 0;
            endpointState.dashboard.etag = null;
            endpointState.events.etag = null;
            await refresh();
          }

          function scheduleRefresh(delay = refreshMs) {
            clearTimeout(refreshTimer);
            refreshTimer = setTimeout(() => {
              refresh().catch(renderError).finally(() => scheduleRefresh());
            }, delay);
          }

          function renderError(error) {
            endpointState.dashboard.error = String(error);
            setStatus();
            renderSections();
          }

          function setupControls() {
            const search = document.getElementById("task-search");
            search?.addEventListener("input", (event) => {
              taskSearchQuery = event.target?.value || "";
              renderTasks();
            });
          }

          setupControls();
          refresh().catch(renderError).finally(() => scheduleRefresh());
        </script>
        """
    )
    return (
        script.replace("__REFRESH_MS__", json.dumps(refresh_ms))
        .replace("__DEFAULT_TASK_REF__", _safe_script_literal(task_ref))
        .strip()
    )


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
