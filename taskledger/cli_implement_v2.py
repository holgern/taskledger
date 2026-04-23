from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.task_runs import (
    add_change,
    finish_implementation,
    log_implementation,
    start_implementation,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
)
from taskledger.errors import LaunchError


def register_implement_v2_commands(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = start_implementation(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"started implementation {payload['run_id']}",
        )

    @app.command("log")
    def log_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        message: Annotated[str, typer.Option("--message")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            run = log_implementation(state.cwd, task_ref, message=message)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged implementation {run.run_id}")

    @app.command("add-change")
    def add_change_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            change = add_change(
                state.cwd,
                task_ref,
                path=path,
                kind=kind,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, change.to_dict(), human=f"logged change {change.change_id}")

    @app.command("finish")
    def finish_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        summary: Annotated[str, typer.Option("--summary")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = finish_implementation(state.cwd, task_ref, summary=summary)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"finished implementation {payload['run_id']}",
        )
