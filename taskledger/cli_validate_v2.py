from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.task_runs import (
    add_validation_check,
    finish_validation,
    show_task_run,
    start_validation,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    resolve_cli_task,
)
from taskledger.errors import LaunchError


def register_validate_v2_commands(app: typer.Typer) -> None:
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
            payload = start_validation(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"started validation {payload['run_id']}")

    def _emit_check(
        ctx: typer.Context,
        *,
        name: str | None,
        criterion: str | None,
        status: str,
        details: str | None,
        evidence: list[str] | None,
        task_ref: str | None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = add_validation_check(
                state.cwd,
                task.id,
                name=name,
                criterion_id=criterion,
                status=status,
                details=details,
                evidence=tuple(evidence or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"added check to {run.run_id}")

    @app.command("check")
    def check_command(
        ctx: typer.Context,
        criterion: Annotated[str, typer.Option("--criterion")],
        status: Annotated[str, typer.Option("--status")] = "pass",
        evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
        name: Annotated[str | None, typer.Option("--name")] = None,
        details: Annotated[str | None, typer.Option("--details")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_check(
            ctx,
            name=name,
            criterion=criterion,
            status=status,
            details=details,
            evidence=evidence,
            task_ref=task_ref,
        )

    @app.command("add-check")
    def add_check_command(
        ctx: typer.Context,
        name: Annotated[str | None, typer.Option("--name")] = None,
        criterion: Annotated[str | None, typer.Option("--criterion")] = None,
        status: Annotated[str, typer.Option("--status")] = "pass",
        details: Annotated[str | None, typer.Option("--details")] = None,
        evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_check(
            ctx,
            name=name,
            criterion=criterion,
            status=status,
            details=details,
            evidence=evidence,
            task_ref=task_ref,
        )

    @app.command("finish")
    def finish_command(
        ctx: typer.Context,
        result: Annotated[str, typer.Option("--result")],
        summary: Annotated[str, typer.Option("--summary")],
        recommendation: Annotated[str | None, typer.Option("--recommendation")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = finish_validation(
                state.cwd,
                task.id,
                result=result,
                summary=summary,
                recommendation=recommendation,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"finished validation {payload['run_id']}")

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
                run_type="validation",
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        run = payload["run"]
        assert isinstance(run, dict)
        emit_payload(ctx, payload, human=f"{run['run_id']}  {run['status']}")
