from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.task_runs import (
    add_change,
    add_implementation_artifact,
    add_implementation_deviation,
    finish_implementation,
    log_implementation,
    run_implementation_command,
    scan_changes,
    show_task_run,
    start_implementation,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    resolve_cli_task,
)
from taskledger.errors import LaunchError


def register_implement_v2_commands(app: typer.Typer) -> None:  # noqa: C901
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = start_implementation(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"started implementation {payload['run_id']}",
        )

    @app.command("log")
    def log_command(
        ctx: typer.Context,
        message: Annotated[str, typer.Option("--message")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = log_implementation(state.cwd, task.id, message=message)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged implementation {run.run_id}")

    def _emit_change_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
        command: Annotated[str | None, typer.Option("--command")] = None,
        git_diff_stat: Annotated[str | None, typer.Option("--git-diff-stat")] = None,
        task_ref: str | None = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            change = add_change(
                state.cwd,
                task.id,
                path=path,
                kind=kind,
                summary=summary,
                command=command,
                git_diff_stat=git_diff_stat,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, change.to_dict(), human=f"logged change {change.change_id}")

    @app.command("change")
    def change_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
        command: Annotated[str | None, typer.Option("--command")] = None,
        git_diff_stat: Annotated[str | None, typer.Option("--git-diff-stat")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_change_command(ctx, path, kind, summary, command, git_diff_stat, task_ref)

    @app.command("add-change")
    def add_change_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
        command: Annotated[str | None, typer.Option("--command")] = None,
        git_diff_stat: Annotated[str | None, typer.Option("--git-diff-stat")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_change_command(ctx, path, kind, summary, command, git_diff_stat, task_ref)

    @app.command("scan-changes")
    def scan_changes_command(
        ctx: typer.Context,
        from_git: Annotated[bool, typer.Option("--from-git")] = False,
        summary: Annotated[str, typer.Option("--summary")] = "",
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            change = scan_changes(
                state.cwd,
                task.id,
                from_git=from_git,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, change.to_dict(), human=f"logged change {change.change_id}")

    @app.command(
        "command",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def command_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        argv = tuple(ctx.args)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = run_implementation_command(
                state.cwd,
                task.id,
                argv=argv,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"ran implementation command exit={payload['exit_code']}",
        )

    @app.command("deviation")
    def deviation_command(
        ctx: typer.Context,
        message: Annotated[str, typer.Option("--message")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = add_implementation_deviation(state.cwd, task.id, message=message)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged deviation on {run.run_id}")

    @app.command("artifact")
    def artifact_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        summary: Annotated[str, typer.Option("--summary")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = add_implementation_artifact(
                state.cwd,
                task.id,
                path=path,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged artifact on {run.run_id}")

    @app.command("finish")
    def finish_command(
        ctx: typer.Context,
        summary: Annotated[str, typer.Option("--summary")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = finish_implementation(state.cwd, task.id, summary=summary)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"finished implementation {payload['run_id']}",
        )

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        run_id: Annotated[str | None, typer.Option("--run")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = show_task_run(
                state.cwd,
                task.id,
                run_id=run_id,
                run_type="implementation",
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        run = payload["run"]
        assert isinstance(run, dict)
        emit_payload(ctx, payload, human=f"{run['run_id']}  {run['status']}")
