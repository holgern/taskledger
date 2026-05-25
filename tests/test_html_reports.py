from __future__ import annotations

from pathlib import Path

from taskledger.services.html_reports import (
    HtmlReportOptions,
    HtmlSiteOptions,
    render_task_report_html,
    write_html_site,
)
from taskledger.services.tasks import create_task
from tests.support.builders import (
    create_approved_task,
    create_done_task,
    init_workspace,
)


def test_render_task_report_html_contains_semantic_sections(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_done_task(ws, allow_lint_errors=True)
    payload = render_task_report_html(ws, task_id)
    html = str(payload["content"])
    assert html.startswith("<!DOCTYPE html>")
    assert "<main>" in html
    assert 'id="summary"' in html
    assert 'id="next-action"' in html
    assert 'id="todos"' in html
    assert 'id="validation"' in html


def test_render_task_report_html_escapes_task_content(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    task = create_task(
        ws,
        title='Bad <script>alert("x")</script>',
        slug="escape-test",
        description='desc <img src=x onerror="boom">',
    )
    payload = render_task_report_html(ws, task.id)
    html = str(payload["content"])
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert "&lt;img src=x onerror=" in html


def test_render_task_report_html_omits_meta_refresh_by_default(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_done_task(ws, allow_lint_errors=True)
    payload = render_task_report_html(ws, task_id)
    html = str(payload["content"])
    assert 'http-equiv="refresh"' not in html


def test_render_task_report_html_includes_meta_refresh_when_requested(
    tmp_path: Path,
) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_done_task(ws, allow_lint_errors=True)
    payload = render_task_report_html(
        ws, task_id, options=HtmlReportOptions(refresh_seconds=2)
    )
    html = str(payload["content"])
    assert '<meta http-equiv="refresh" content="2" />' in html


def test_render_task_report_html_has_no_script_or_fetch_tokens(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_done_task(ws, allow_lint_errors=True)
    payload = render_task_report_html(ws, task_id)
    html = str(payload["content"])
    assert "<script" not in html.lower()
    assert "fetch(" not in html
    assert "setTimeout" not in html
    assert "setInterval" not in html
    assert "dashboard.js" not in html
    assert "dashboard.css" not in html


def test_write_html_site_writes_index_and_task_pages(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    output_dir = tmp_path / ".taskledger-report"
    payload = write_html_site(ws, output_dir, options=HtmlSiteOptions())
    assert payload["kind"] == "html_report_site_written"
    written_paths = {path.name for path in output_dir.rglob("*") if path.is_file()}
    assert "index.html" in written_paths
    assert any(
        name.startswith("task-") and name.endswith(".html") for name in written_paths
    )


def test_write_html_site_does_not_write_css_or_js_assets(tmp_path: Path) -> None:
    ws = init_workspace(tmp_path)
    create_done_task(ws, allow_lint_errors=True)
    output_dir = tmp_path / ".taskledger-report"
    write_html_site(ws, output_dir, options=HtmlSiteOptions())
    file_names = [str(path) for path in output_dir.rglob("*") if path.is_file()]
    assert not any(name.endswith(".js") or name.endswith(".css") for name in file_names)


def test_render_task_report_html_renders_task_markdown_and_escapes_html(
    tmp_path: Path,
) -> None:
    ws = init_workspace(tmp_path)
    task = create_task(
        ws,
        title="Markdown task",
        slug="markdown-task",
        description=(
            "## User-facing details\n\n"
            "This has **bold text** and `inline code`.\n\n"
            "- item one\n"
            "- item two\n\n"
            "<script>alert('x')</script>"
        ),
    )

    payload = render_task_report_html(ws, task.id)
    html = str(payload["content"])

    assert "<h2>User-facing details</h2>" in html
    assert "<strong>bold text</strong>" in html
    assert "<code>inline code</code>" in html
    assert "<li>item one</li>" in html
    assert "<script" not in html.lower()
    assert "&lt;script&gt;alert" in html


def test_render_task_report_html_renders_accepted_plan_markdown(
    tmp_path: Path,
) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_approved_task(
        ws,
        allow_lint_errors=True,
        plan_text="""---
goal: Render plan markdown.
acceptance_criteria:
  - id: ac-0001
    text: Plan markdown renders in HTML.
todos:
  - id: todo-0001
    text: Implement rendering.
    validation_hint: pytest tests/test_html_reports.py
---

## Goal

Render **plan Markdown** and `inline code`.

## Implementation notes

- Use the canonical Markdown report renderer.
""",
    )

    payload = render_task_report_html(ws, task_id)
    html = str(payload["content"])

    # Plan body headings rendered as HTML
    assert "<h2>Goal</h2>" in html
    assert "<strong>plan Markdown</strong>" in html
    assert "<code>inline code</code>" in html
    assert "<li>Use the canonical Markdown report renderer.</li>" in html


def test_render_task_report_html_does_not_show_raw_relationship_or_validation_dicts(
    tmp_path: Path,
) -> None:
    ws = init_workspace(tmp_path)
    task_id = create_done_task(ws, allow_lint_errors=True)

    payload = render_task_report_html(ws, task_id)
    html = str(payload["content"])

    # Raw Python dict reprs should not appear
    assert "{'kind':" not in html
    assert "'parent_task':" not in html
    # Structured sections should have proper headings
    assert '<h2 id="relationships">Relationships</h2>' in html
    assert '<h2 id="validation">Validation</h2>' in html
