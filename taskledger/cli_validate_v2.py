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
)
from taskledger.errors import LaunchError


def register_validate_v2_commands(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = start_validation(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"started validation {payload['run_id']}")

    def _emit_check(
        ctx: typer.Context,
        task_ref: str,
        *,
        name: str | None,
        criterion: str | None,
        status: str,
        details: str | None,
        evidence: list[str] | None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            run = add_validation_check(
                state.cwd,
                task_ref,
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
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        criterion: Annotated[str, typer.Option("--criterion")],
        status: Annotated[str, typer.Option("--status")] = "pass",
        evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
        name: Annotated[str | None, typer.Option("--name")] = None,
        details: Annotated[str | None, typer.Option("--details")] = None,
    ) -> None:
        _emit_check(
            ctx,
            task_ref,
            name=name,
            criterion=criterion,
            status=status,
            details=details,
            evidence=evidence,
        )

    @app.command("add-check")
    def add_check_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        name: Annotated[str | None, typer.Option("--name")] = None,
        criterion: Annotated[str | None, typer.Option("--criterion")] = None,
        status: Annotated[str, typer.Option("--status")] = "pass",
        details: Annotated[str | None, typer.Option("--details")] = None,
        evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
    ) -> None:
        _emit_check(
            ctx,
            task_ref,
            name=name,
            criterion=criterion,
            status=status,
            details=details,
            evidence=evidence,
        )

    @app.command("finish")
    def finish_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        result: Annotated[str, typer.Option("--result")],
        summary: Annotated[str, typer.Option("--summary")],
        recommendation: Annotated[str | None, typer.Option("--recommendation")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = finish_validation(
                state.cwd,
                task_ref,
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
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        run_id: Annotated[str | None, typer.Option("--run")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_task_run(
                state.cwd,
                task_ref,
                run_id=run_id,
                run_type="validation",
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        run = payload["run"]
        assert isinstance(run, dict)
        emit_payload(ctx, payload, human=f"{run['run_id']}  {run['status']}")
