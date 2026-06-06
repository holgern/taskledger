"""Textual application entrypoint for ``taskledger tui``.

This module imports Textual. It is loaded lazily by the ``tui`` CLI command,
so ``taskledger --help`` and other commands never trigger the textual import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import (
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
)

from taskledger.errors import LaunchError
from taskledger.services.tui_read_model import load_tui_snapshot
from taskledger.tui import widgets as tui_widgets

# Stage filter shortcuts: key -> (label, statuses to keep). Empty tuple means
# "all". A stage filter value of None means "no filtering applied".
_STAGE_FILTERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "a": ("all", ()),
    "n": ("plan_review", ("plan_review",)),
    "p": ("planning", ("planning",)),
    "i": ("implementing", ("implementing",)),
    "m": ("implemented", ("implemented",)),
    "v": ("validating", ("validating",)),
    "f": ("failed_validation", ("failed_validation",)),
    "d": ("done", ("done",)),
    "c": ("cancelled", ("cancelled",)),
}


class CommandCopyModal(Static):
    """Simple modal-style widget that displays the next-action commands.

    Textual modal screens are heavier than we need for the MVP.
    This widget is pushed onto a normal Static overlay region
    by :meth:`TaskledgerTui.action_copy_command`.
    """

    DEFAULT_CSS = """
    CommandCopyModal {
        layer: overlay;
        width: 80;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $panel;
        color: $text;
    }
    """

    def __init__(self, commands: list[str], primary: str | None) -> None:
        super().__init__()
        self._commands = commands
        self._primary = primary

    def render(self) -> str:
        lines: list[str] = ["Command palette  — press Esc or c to dismiss", ""]
        if self._primary:
            lines.append("Primary:")
            lines.append(f"  $ {self._primary}")
            lines.append("")
        if self._commands:
            lines.append("All commands:")
            for command in self._commands:
                lines.append(f"  $ {command}")
        else:
            lines.append("No commands available for the current selection.")
        lines.append("")
        lines.append(
            "Copy with your terminal's selection shortcut or by selecting the line."
        )
        return "\n".join(lines)


class HelpOverlay(Static):
    DEFAULT_CSS = """
    HelpOverlay {
        layer: overlay;
        width: 80;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        border: thick $primary;
        background: $panel;
        color: $text;
    }
    """

    def render(self) -> str:
        lines = [
            "taskledger tui — read-only navigator",
            "",
            "Key bindings:",
            "  q          quit",
            "  r / F5     refresh snapshot",
            "  /          focus search/filter input",
            "  Enter      open selected task",
            "  Tab        cycle focus / tabs",
            "  1..9       jump to a tab",
            "  c          show command copy palette",
            "  o          write a static HTML report for the selected task",
            "  a n p i m v f d c   stage filters",
            "  t          toggle archived tasks",
            "  ?          this help",
            "",
            "This TUI is read-only. Mutating actions still require the CLI.",
        ]
        return "\n".join(lines)


def _safe_query_one(app: App[None], selector: str, widget_type: type) -> Any:
    """Return the queried widget or None if it does not (yet) exist.

    Keeps the renderer paths free of broad ``except Exception`` blocks.
    """

    try:
        return app.query_one(selector, widget_type)
    except NoMatches:
        return None


class TaskledgerTui(App[None]):
    """Read-only Textual navigator over the taskledger read models."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main { height: 1fr; }
    #tasks-pane { width: 34; border-right: solid $primary; }
    #detail-pane { width: 2fr; }
    #summary { padding: 0 1; height: auto; max-height: 12; }
    #filter-input { dock: top; margin: 0 0 1 0; }
    #status-bar { dock: bottom; height: 1; background: $boost; color: $text; }
    ListView > ListItem { padding: 0 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("f5", "refresh", "Refresh", show=False),
        Binding("slash", "focus_filter", "Filter", show=False),
        Binding("c", "copy_command", "Copy cmd"),
        Binding("o", "open_report", "Open report"),
        Binding("t", "toggle_archived", "Toggle archived"),
        Binding("question_mark", "help", "Help", show=False),
        Binding("escape", "dismiss_overlay", "Dismiss", show=False),
        Binding("1", "switch_tab('summary')", "Summary", show=False),
        Binding("2", "switch_tab('plan')", "Plan", show=False),
        Binding("3", "switch_tab('todos')", "Todos", show=False),
        Binding("4", "switch_tab('implementation')", "Impl", show=False),
        Binding("5", "switch_tab('reviews')", "Reviews", show=False),
        Binding("6", "switch_tab('validation')", "Valid", show=False),
        Binding("7", "switch_tab('files')", "Files", show=False),
        Binding("8", "switch_tab('events')", "Events", show=False),
        Binding("9", "switch_tab('raw-report')", "Raw", show=False),
    ]
    # Stage filter bindings are generated dynamically because they overlap
    # with tab-switching keys (we use letters that aren't 1..9).
    for _key, (_label, _statuses) in _STAGE_FILTERS.items():
        if _key in {"a", "n", "p", "i", "m", "v", "f", "d", "c"}:
            BINDINGS.append(
                Binding(
                    _key,
                    f"filter_stage('{_key}')",
                    f"Filter {_label}",
                    show=False,
                )
            )
    del _key, _label, _statuses

    def __init__(
        self,
        *,
        workspace_root: Path,
        task_ref: str | None = None,
        refresh_seconds: int | None = None,
        include_archived: bool = False,
    ) -> None:
        super().__init__()
        self.workspace_root = workspace_root
        self.task_ref = task_ref
        self.refresh_seconds = refresh_seconds
        self.include_archived = include_archived
        self.snapshot: dict[str, Any] = {}
        self._stage_filter: tuple[str, ...] = ()  # empty = all
        self._filter_text = ""
        self._refresh_timer: Any = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="tasks-pane"):
                yield Input(
                    placeholder="/ filter by id, slug, title, label",
                    id="filter-input",
                )
                yield ListView(id="tasks")
            with Vertical(id="detail-pane"):
                with VerticalScroll(id="summary-scroll"):
                    yield Static(
                        "Loading…\nPress r to refresh or q to quit.",
                        id="summary",
                    )
                with TabbedContent(id="tabs"):
                    yield TabPane("Summary", Static(id="summary-tab"), id="summary")
                    yield TabPane("Plan", Static(id="plan-tab"), id="plan")
                    yield TabPane("Todos", Static(id="todos-tab"), id="todos")
                    yield TabPane(
                        "Implementation",
                        Static(id="implementation-tab"),
                        id="implementation",
                    )
                    yield TabPane("Reviews", Static(id="reviews-tab"), id="reviews")
                    yield TabPane(
                        "Validation",
                        Static(id="validation-tab"),
                        id="validation",
                    )
                    yield TabPane("Files", Static(id="files-tab"), id="files")
                    yield TabPane("Events", Static(id="events-tab"), id="events")
                    yield TabPane(
                        "Raw Report", Static(id="raw-report-tab"), id="raw-report"
                    )
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self._refresh_timer = self.set_interval(
                self.refresh_seconds, self.action_refresh
            )

    # ------------------------------------------------------------------
    # Snapshot refresh and rendering
    # ------------------------------------------------------------------

    def action_refresh(self) -> None:
        try:
            self.snapshot = load_tui_snapshot(
                self.workspace_root,
                task_ref=self.task_ref,
                include_events=True,
                include_archived=self.include_archived,
            )
        except LaunchError as exc:
            self._set_status(f"refresh blocked: {exc.code}: {exc.message}")
            return
        except OSError as exc:
            self._set_status(f"refresh io error: {exc}")
            return
        self._render_snapshot()

    def _render_snapshot(self) -> None:
        self._render_task_list()
        self._render_detail()
        self._set_status(self._render_status_text())

    def _render_status_text(self) -> str:
        selected = self.snapshot.get("selected")
        if not isinstance(selected, dict):
            return "no task selected"
        task_raw = selected.get("task")
        task: dict[str, Any] = task_raw if isinstance(task_raw, dict) else {}
        na_raw = selected.get("next_action")
        next_action: dict[str, Any] = na_raw if isinstance(na_raw, dict) else {}
        parts = [
            str(task.get("id", "")),
            str(task.get("status_stage", "")),
        ]
        if next_action.get("action"):
            parts.append(f"next: {next_action.get('action')}")
        if self._stage_filter:
            label = "+".join(self._stage_filter) or "all"
            parts.append(f"filter: {label}")
        if self._filter_text:
            parts.append(f"search: {self._filter_text}")
        return " | ".join(part for part in parts if part)

    def _set_status(self, text: str) -> None:
        widget = _safe_query_one(self, "#status-bar", Static)
        if widget is not None:
            widget.update(text)

    # ------------------------------------------------------------------
    # Task list rendering
    # ------------------------------------------------------------------

    def _iter_candidate_tasks(self) -> list[dict[str, Any]]:
        visible = list(self.snapshot.get("tasks") or [])
        archived = list(self.snapshot.get("archived_tasks") or [])
        return visible + archived

    def _matches_filters(self, task: dict[str, Any]) -> bool:
        if self._stage_filter:
            status = str(task.get("status_stage") or "")
            if status not in self._stage_filter:
                return False
        if self._filter_text:
            haystack_parts = [
                str(task.get("id") or ""),
                str(task.get("slug") or ""),
                str(task.get("title") or ""),
            ]
            labels = task.get("labels") or []
            if labels:
                haystack_parts.extend(str(label) for label in labels)
            haystack = " ".join(haystack_parts).lower()
            if self._filter_text.lower() not in haystack:
                return False
        return True

    def _render_task_list(self) -> None:
        task_list = _safe_query_one(self, "#tasks", ListView)
        if task_list is None:
            return
        task_list.clear()
        active_task_id = ""
        project = self.snapshot.get("project") or {}
        active = project.get("active_task") if isinstance(project, dict) else None
        if isinstance(active, dict):
            active_task_id = str(active.get("task_id") or "")
        for task in self._iter_candidate_tasks():
            if not self._matches_filters(task):
                continue
            marker = "*" if task.get("id") == active_task_id else " "
            archived = " (archived)" if task.get("archived") else ""
            label = (
                f"{marker} {task.get('id', '')} "
                f"[{task.get('status_stage', '')}]"
                f"{archived} {task.get('title', '')}"
            )
            task_list.append(ListItem(Static(label)))

    def _render_detail(self) -> None:
        selected = self.snapshot.get("selected")
        self._update_static("#summary-tab", tui_widgets.render_summary(selected))
        self._update_static(
            "#plan-tab",
            tui_widgets.render_plan(
                self.snapshot.get("plan_review_markdown"), selected
            ),
        )
        self._update_static("#todos-tab", tui_widgets.render_todos(selected))
        self._update_static(
            "#implementation-tab", tui_widgets.render_implementation(selected)
        )
        self._update_static(
            "#reviews-tab",
            tui_widgets.render_reviews(self.snapshot.get("reviews") or []),
        )
        self._update_static("#validation-tab", tui_widgets.render_validation(selected))
        self._update_static("#files-tab", tui_widgets.render_files(selected))
        self._update_static("#events-tab", tui_widgets.render_events(selected))
        self._update_static(
            "#raw-report-tab",
            tui_widgets.render_raw_report(self.snapshot.get("report_markdown")),
        )

        target_tab = tui_widgets.default_tab_for_selected(selected)
        tabs = _safe_query_one(self, "#tabs", TabbedContent)
        if tabs is not None:
            tabs.active = target_tab

    def _update_static(self, selector: str, content: str) -> None:
        widget = _safe_query_one(self, selector, Static)
        if widget is not None:
            widget.update(content)

    # ------------------------------------------------------------------
    # List + input events
    # ------------------------------------------------------------------

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        # Each ListItem's first child is the Static that holds the label.
        text = ""
        try:
            label_widget = next(iter(item.children))
            text = str(getattr(label_widget, "renderable", "") or "")
        except (StopIteration, IndexError):
            pass
        # Label format: "{marker} {task_id} [...]"
        parts = text.split()
        if len(parts) >= 2:
            self.task_ref = parts[1]
            self.action_refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter-input":
            return
        self._filter_text = event.value.strip()
        self._render_task_list()
        self._set_status(self._render_status_text())

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def action_focus_filter(self) -> None:
        widget = _safe_query_one(self, "#filter-input", Input)
        if widget is not None:
            widget.focus()

    def action_filter_stage(self, key: str) -> None:
        spec = _STAGE_FILTERS.get(key)
        if spec is None:
            return
        _, statuses = spec
        self._stage_filter = statuses
        self._render_task_list()
        self._set_status(self._render_status_text())

    def action_toggle_archived(self) -> None:
        self.include_archived = not self.include_archived
        self.action_refresh()

    def action_copy_command(self) -> None:
        selected = self.snapshot.get("selected")
        if not isinstance(selected, dict):
            self._set_status("no task selected")
            return
        na_raw = selected.get("next_action")
        next_action: dict[str, Any] = na_raw if isinstance(na_raw, dict) else {}
        commands: list[str] = []
        for entry in next_action.get("commands") or []:
            if isinstance(entry, dict):
                cmd = entry.get("command")
                if isinstance(cmd, str) and cmd:
                    commands.append(cmd)
            elif isinstance(entry, str):
                commands.append(entry)
        primary: str | None = None
        if isinstance(next_action.get("next_command"), str):
            primary = next_action["next_command"]
        if not commands and not primary:
            self._set_status("no commands available")
            return
        self.push_screen(_CommandScreen(commands, primary))  # type: ignore[call-overload]

    def action_open_report(self) -> None:
        selected = self.snapshot.get("selected")
        if not isinstance(selected, dict):
            self._set_status("no task selected")
            return
        task_raw = selected.get("task")
        task: dict[str, Any] = task_raw if isinstance(task_raw, dict) else {}
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            self._set_status("selected task has no id")
            return
        try:
            from taskledger.services.html_reports import (
                HtmlReportOptions,
                render_task_report_html,
            )
        except ImportError as exc:
            self._set_status(f"html reports unavailable: {exc}")
            return
        try:
            payload = render_task_report_html(
                self.workspace_root,
                task_id,
                options=HtmlReportOptions(),
            )
        except LaunchError as exc:
            self._set_status(f"report blocked: {exc.code}: {exc.message}")
            return
        except OSError as exc:
            self._set_status(f"report io error: {exc}")
            return
        content = payload.get("html") if isinstance(payload, dict) else None
        if not isinstance(content, str):
            self._set_status("report payload missing html")
            return
        target = self.workspace_root / f"{task_id}.tui-report.html"
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            self._set_status(f"report write failed: {exc}")
            return
        self._set_status(f"static report written to {target}")

    def action_dismiss_overlay(self) -> None:
        # Textual's pop_screen handles the modal screen; if no modal screen is
        # active this raises ScreenStackError, which we ignore.
        try:
            self.pop_screen()
        except self._ScreenStackError:
            return

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = _safe_query_one(self, "#tabs", TabbedContent)
        if tabs is not None:
            tabs.active = tab_id

    def action_help(self) -> None:
        self.push_screen(_HelpScreen())  # type: ignore[call-overload]

    # Alias for the ScreenStackError type without forcing callers to import it.
    from textual.app import ScreenStackError as _ScreenStackError


class _CommandScreen(CommandCopyModal):
    """Screen wrapper so the modal can be popped via App.push_screen."""

    BINDINGS = [Binding("escape", "app.pop_screen", "Close", show=False)]
    BINDINGS.append(Binding("c", "app.pop_screen", "Close", show=False))


class _HelpScreen(HelpOverlay):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close", show=False)]
    BINDINGS.append(Binding("question_mark", "app.pop_screen", "Close", show=False))
    BINDINGS.append(Binding("?", "app.pop_screen", "Close", show=False))


def run_tui(
    *,
    workspace_root: Path,
    task_ref: str | None = None,
    refresh_seconds: int | None = None,
    include_archived: bool = False,
) -> None:
    """Launch the Textual app. Blocking; returns when the user quits."""

    app_instance = TaskledgerTui(
        workspace_root=workspace_root,
        task_ref=task_ref,
        refresh_seconds=refresh_seconds,
        include_archived=include_archived,
    )
    app_instance.run()
