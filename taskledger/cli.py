from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.project import (
    init_project,
    project_export,
    project_import,
    project_snapshot,
    project_status,
    project_status_summary,
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
from taskledger.cli_implement_v2 import register_implement_v2_commands
from taskledger.cli_misc_v2 import (
    emit_can_command,
    emit_doctor_command,
    emit_doctor_locks_command,
    emit_next_action_command,
    emit_reindex_command,
    register_file_v2_commands,
    register_handoff_v2_commands,
    register_intro_v2_commands,
    register_lock_v2_commands,
    register_require_v2_commands,
    register_todo_v2_commands,
)
from taskledger.cli_plan_v2 import register_plan_v2_commands
from taskledger.cli_question_v2 import register_question_v2_commands
from taskledger.cli_task_v2 import register_task_v2_commands
from taskledger.cli_validate_v2 import register_validate_v2_commands
from taskledger.errors import LaunchError

app = typer.Typer(add_completion=False, help="Manage staged taskledger coding work.")
task_app = typer.Typer(add_completion=False, help="Manage coding tasks.")
plan_app = typer.Typer(add_completion=False, help="Manage plan versions.")
question_app = typer.Typer(add_completion=False, help="Manage planning questions.")
implement_app = typer.Typer(add_completion=False, help="Manage implementation runs.")
validate_app = typer.Typer(add_completion=False, help="Manage validation runs.")
todo_app = typer.Typer(add_completion=False, help="Manage task todos.")
intro_app = typer.Typer(add_completion=False, help="Manage shared introductions.")
file_app = typer.Typer(add_completion=False, help="Manage linked files.")
require_app = typer.Typer(add_completion=False, help="Manage task requirements.")
lock_app = typer.Typer(add_completion=False, help="Inspect and repair locks.")
handoff_app = typer.Typer(add_completion=False, help="Render fresh-context handoffs.")
doctor_app = typer.Typer(
    add_completion=False,
    help="Inspect taskledger integrity.",
    invoke_without_command=True,
)

app.add_typer(task_app, name="task")
app.add_typer(plan_app, name="plan")
app.add_typer(question_app, name="question")
app.add_typer(implement_app, name="implement")
app.add_typer(validate_app, name="validate")
app.add_typer(todo_app, name="todo")
app.add_typer(intro_app, name="intro")
app.add_typer(file_app, name="file")
app.add_typer(require_app, name="require")
app.add_typer(lock_app, name="lock")
app.add_typer(handoff_app, name="handoff")
app.add_typer(doctor_app, name="doctor")

register_task_v2_commands(task_app)
register_plan_v2_commands(plan_app)
register_question_v2_commands(question_app)
register_implement_v2_commands(implement_app)
register_validate_v2_commands(validate_app)
register_todo_v2_commands(todo_app)
register_intro_v2_commands(intro_app)
register_file_v2_commands(file_app)
register_require_v2_commands(require_app)
register_lock_v2_commands(lock_app)
register_handoff_v2_commands(handoff_app)


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
def status_command(
    ctx: typer.Context,
    full: Annotated[
        bool,
        typer.Option(
            "--full",
            help="Show the full status payload instead of the compact summary.",
        ),
    ] = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        payload = (
            project_status(state.cwd) if full else project_status_summary(state.cwd)
        )
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(ctx, payload)


@doctor_app.callback()
def doctor_command(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    emit_doctor_command(ctx)


@doctor_app.command("locks")
def doctor_locks_command(ctx: typer.Context) -> None:
    emit_doctor_locks_command(ctx)


@app.command("next-action")
def next_action_command(
    ctx: typer.Context,
    task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
) -> None:
    emit_next_action_command(ctx, task_ref)


@app.command("can")
def can_command(
    ctx: typer.Context,
    task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    action: Annotated[str, typer.Argument(..., help="Action name.")],
) -> None:
    emit_can_command(ctx, task_ref, action)


@app.command("reindex")
def reindex_command(ctx: typer.Context) -> None:
    emit_reindex_command(ctx)


@app.command("export")
def export_command(
    ctx: typer.Context,
    include_bodies: Annotated[
        bool,
        typer.Option("--include-bodies", help="Include Markdown bodies in the export."),
    ] = False,
    include_run_artifacts: Annotated[
        bool,
        typer.Option(
            "--include-run-artifacts",
            help="Include run artifact files in the export payload.",
        ),
    ] = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    payload = project_export(
        state.cwd,
        include_bodies=include_bodies,
        include_run_artifacts=include_run_artifacts,
    )
    emit_payload(ctx, payload, human="exported taskledger state")


@app.command("import")
def import_command(
    ctx: typer.Context,
    source: Annotated[Path, typer.Argument(..., exists=True, readable=True)],
    replace: Annotated[
        bool,
        typer.Option("--replace", help="Replace existing taskledger state."),
    ] = False,
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    text = source.read_text(encoding="utf-8")
    try:
        payload = project_import(state.cwd, text=text, replace=replace)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(ctx, payload, human="imported taskledger state")


@app.command("snapshot")
def snapshot_command(
    ctx: typer.Context,
    output_dir: Annotated[Path, typer.Argument(..., file_okay=False, dir_okay=True)],
    include_bodies: Annotated[
        bool,
        typer.Option(
            "--include-bodies",
            help="Include Markdown bodies in the snapshot export.",
        ),
    ] = False,
    include_run_artifacts: Annotated[
        bool,
        typer.Option(
            "--include-run-artifacts",
            help="Include run artifact files in the snapshot export.",
        ),
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
    emit_payload(ctx, payload, human=f"wrote snapshot to {payload['snapshot_dir']}")


@app.command("search")
def search_command(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(..., help="Search query.")],
    repo_refs: Annotated[list[str] | None, typer.Option("--repo")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 50,
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
    pattern: Annotated[str, typer.Argument(..., help="Regex pattern.")],
    repo_refs: Annotated[list[str] | None, typer.Option("--repo")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 100,
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
    repo_refs: Annotated[list[str] | None, typer.Option("--repo")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 50,
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
    module: Annotated[str, typer.Argument(..., help="Module path.")],
) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        payload = dependencies_for_module(
            state.cwd,
            repo_ref=repo_ref,
            module=module,
        )
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(ctx, payload)


def _emit_search_results(ctx: typer.Context, factory, *, title: str) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        results = factory(state.cwd)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    human = (
        "\n".join([title, *[item.path for item in results]])
        if results
        else f"{title}\n(empty)"
    )
    emit_payload(ctx, [item.to_dict() for item in results], human=human)


def cli_main() -> None:
    app()
