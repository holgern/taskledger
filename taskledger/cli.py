from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.project import (
    init_project,
    project_board,
    project_doctor,
    project_export,
    project_import,
    project_next,
    project_report,
    project_snapshot,
    project_status,
)
from taskledger.api.search import (
    dependencies_for_module,
    grep_workspace,
    search_workspace,
    symbols_workspace,
)
from taskledger.cli_common import (
    CLIState,
    emit_error,
    emit_payload,
    resolve_workspace_root,
)
from taskledger.cli_compose import register_compose_commands
from taskledger.cli_context import register_context_commands
from taskledger.cli_execution_requests import register_execution_request_commands
from taskledger.cli_item import register_item_commands
from taskledger.cli_memory import register_memory_commands
from taskledger.cli_repo import register_repo_commands
from taskledger.cli_runs import register_runs_commands
from taskledger.cli_runtime_support import register_runtime_support_commands
from taskledger.cli_validation import register_validation_commands
from taskledger.cli_workflow import register_workflow_commands
from taskledger.errors import LaunchError

app = typer.Typer(add_completion=False, help="Manage durable taskledger project state.")
item_app = typer.Typer(add_completion=False, help="Manage work items.")
memory_app = typer.Typer(add_completion=False, help="Manage memories.")
context_app = typer.Typer(add_completion=False, help="Manage contexts.")
repo_app = typer.Typer(add_completion=False, help="Manage repos.")
runs_app = typer.Typer(add_completion=False, help="Inspect saved runs.")
validation_app = typer.Typer(add_completion=False, help="Manage validation records.")
workflow_app = typer.Typer(
    add_completion=False,
    help="Manage workflow definitions and stage state.",
)
execution_request_app = typer.Typer(
    add_completion=False,
    help="Build and inspect execution requests.",
)
compose_app = typer.Typer(
    add_completion=False,
    help="Inspect compose selection and bundle payloads.",
)
runtime_support_app = typer.Typer(
    add_completion=False,
    help="Inspect runtime support configuration and helpers.",
)
app.add_typer(item_app, name="item")
app.add_typer(memory_app, name="memory")
app.add_typer(context_app, name="context")
app.add_typer(repo_app, name="repo")
app.add_typer(runs_app, name="runs")
app.add_typer(validation_app, name="validation")
app.add_typer(workflow_app, name="workflow")
app.add_typer(execution_request_app, name="exec-request")
app.add_typer(compose_app, name="compose")
app.add_typer(runtime_support_app, name="runtime-support")
register_item_commands(item_app)
register_memory_commands(memory_app)
register_context_commands(context_app)
register_repo_commands(repo_app)
register_runs_commands(runs_app)
register_validation_commands(validation_app)
register_workflow_commands(workflow_app)
register_execution_request_commands(execution_request_app)
register_compose_commands(compose_app)
register_runtime_support_commands(runtime_support_app)


@app.callback()
def main(
    ctx: typer.Context,
    cwd: Annotated[
        Path | None,
        typer.Option(
            "--cwd",
            help="Workspace root. Defaults to the current directory.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Render machine-readable JSON."),
    ] = False,
) -> None:
    ctx.obj = CLIState(cwd=resolve_workspace_root(cwd), json_output=json_output)


@app.command("init")
def init_command(ctx: typer.Context) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    payload = init_project(state.cwd)
    emit_payload(
        ctx,
        payload,
        human="\n".join(
            [
                f"initialized taskledger: {payload['root']}",
                *[f"- {item}" for item in payload["created"]],
            ]
        ),
    )


@app.command("status")
def status_command(ctx: typer.Context) -> None:
    _emit_project_payload(ctx, project_status)


@app.command("board")
def board_command(ctx: typer.Context) -> None:
    _emit_project_payload(ctx, project_board)


@app.command("next")
def next_command(ctx: typer.Context) -> None:
    _emit_project_payload(ctx, project_next, allow_none=True)


@app.command("doctor")
def doctor_command(ctx: typer.Context) -> None:
    _emit_project_payload(ctx, project_doctor)


@app.command("report")
def report_command(ctx: typer.Context) -> None:
    _emit_project_payload(ctx, project_report)


@app.command("export")
def export_command(
    ctx: typer.Context,
    include_bodies: Annotated[
        bool,
        typer.Option(
            "--include-bodies",
            help="Include saved memory and context bodies.",
        ),
    ] = False,
    include_run_artifacts: Annotated[
        bool,
        typer.Option("--include-run-artifacts", help="Include saved run artifacts."),
    ] = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    emit_payload(
        ctx,
        project_export(
            state.cwd,
            include_bodies=include_bodies,
            include_run_artifacts=include_run_artifacts,
        ),
    )


@app.command("import")
def import_command(
    ctx: typer.Context,
    source: Annotated[Path, typer.Argument(..., help="Export JSON file to import.")],
    replace: Annotated[
        bool,
        typer.Option("--replace", help="Replace current taskledger state."),
    ] = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        text = source.read_text(encoding="utf-8")
        payload = project_import(state.cwd, text=text, replace=replace)
    except (LaunchError, OSError) as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(ctx, payload, human=f"imported taskledger from {source}")


@app.command("snapshot")
def snapshot_command(
    ctx: typer.Context,
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Directory where the snapshot will be created.",
        ),
    ],
    include_bodies: Annotated[
        bool,
        typer.Option(
            "--include-bodies",
            help="Include saved memory and context bodies.",
        ),
    ] = False,
    include_run_artifacts: Annotated[
        bool,
        typer.Option("--include-run-artifacts", help="Include saved run artifacts."),
    ] = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        payload = project_snapshot(
            state.cwd,
            output_dir=output_dir,
            include_bodies=include_bodies,
            include_run_artifacts=include_run_artifacts,
        )
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(ctx, payload)


@app.command("search")
def search_command(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(..., help="Search query.")],
    repo_refs: Annotated[
        list[str] | None,
        typer.Option("--repo", help="Limit the search to one or more repos."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of matches to return."),
    ] = 50,
) -> None:
    _emit_search_results(
        ctx,
        lambda cwd: search_workspace(
            cwd,
            query=query,
            repo_refs=tuple(repo_refs or ()),
            limit=limit,
        ),
        title="SEARCH",
    )


@app.command("grep")
def grep_command(
    ctx: typer.Context,
    pattern: Annotated[str, typer.Argument(..., help="Regular expression to match.")],
    repo_refs: Annotated[
        list[str] | None,
        typer.Option("--repo", help="Limit the grep to one or more repos."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of matches to return."),
    ] = 100,
) -> None:
    _emit_search_results(
        ctx,
        lambda cwd: grep_workspace(
            cwd,
            pattern=pattern,
            repo_refs=tuple(repo_refs or ()),
            limit=limit,
        ),
        title="GREP",
    )


@app.command("symbols")
def symbols_command(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(..., help="Symbol query.")],
    repo_refs: Annotated[
        list[str] | None,
        typer.Option("--repo", help="Limit the symbol scan to one or more repos."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of matches to return."),
    ] = 50,
) -> None:
    _emit_search_results(
        ctx,
        lambda cwd: symbols_workspace(
            cwd,
            query=query,
            repo_refs=tuple(repo_refs or ()),
            limit=limit,
        ),
        title="SYMBOLS",
    )


@app.command("deps")
def deps_command(
    ctx: typer.Context,
    repo_ref: Annotated[str, typer.Argument(..., help="Repo ref.")],
    module: Annotated[str, typer.Argument(..., help="Module name.")],
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        payload = dependencies_for_module(state.cwd, repo_ref=repo_ref, module=module)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(
        ctx,
        payload.to_dict(),
        human="\n".join(
            [
                f"MODULE {payload.module}",
                f"repo: {payload.repo}",
                f"manifest: {payload.manifest_path}",
                f"depends: {', '.join(payload.depends) or '-'}",
            ]
        ),
    )


def _emit_project_payload(
    ctx: typer.Context,
    factory,
    *,
    allow_none: bool = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        payload = factory(state.cwd)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    if payload is None and allow_none:
        emit_payload(ctx, None, human="no next action")
        return
    emit_payload(ctx, payload)


def _emit_search_results(ctx: typer.Context, factory, *, title: str) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        results = factory(state.cwd)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(
        ctx,
        [item.to_dict() for item in results],
        human="\n".join(
            [title]
            + [
                f"{item.repo}:{item.path}:{item.line or '-'}  {item.text}"
                for item in results
            ]
            if results
            else [title, "(empty)"]
        ),
    )


def cli_main() -> None:
    app()
