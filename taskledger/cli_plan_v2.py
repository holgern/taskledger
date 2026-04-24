from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.plans import (
    approve_plan,
    diff_plan,
    list_plan_versions,
    propose_plan,
    reject_plan,
    revise_plan,
    show_plan,
    start_planning,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    read_text_input,
)
from taskledger.errors import LaunchError


def register_plan_v2_commands(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = start_planning(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"started planning {payload['task_id']}")

    @app.command("propose")
    def propose_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        text: Annotated[str | None, typer.Option("--text")] = None,
        from_file: Annotated[Path | None, typer.Option("--file")] = None,
        criterion: Annotated[list[str] | None, typer.Option("--criterion")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = propose_plan(
                state.cwd,
                task_ref,
                body=read_text_input(text=text, from_file=from_file),
                criteria=tuple(criterion or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"proposed plan v{payload['plan_version']} for {payload['task_id']}",
        )

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        version: Annotated[int | None, typer.Option("--version")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_plan(state.cwd, task_ref, version=version)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        plan = payload["plan"]
        assert isinstance(plan, dict)
        emit_payload(
            ctx,
            payload,
            human=f"plan v{plan['plan_version']} ({plan['status']})",
        )

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = list_plan_versions(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        plans = payload["plans"]
        assert isinstance(plans, list)
        lines = ["PLANS"]
        for item in plans:
            if isinstance(item, dict):
                lines.append(f"v{item['plan_version']}  {item['status']}")
        emit_payload(
            ctx, payload, human="\n".join(lines) if plans else "PLANS\n(empty)"
        )

    @app.command("diff")
    def diff_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        from_version: Annotated[int, typer.Option("--from")] = 1,
        to_version: Annotated[int, typer.Option("--to")] = 1,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = diff_plan(
                state.cwd,
                task_ref,
                from_version=from_version,
                to_version=to_version,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=str(payload["diff"]))

    @app.command("approve")
    def approve_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        version: Annotated[int, typer.Option("--version")],
        actor: Annotated[str, typer.Option("--actor")] = "user",
        actor_name: Annotated[str | None, typer.Option("--actor-name")] = None,
        note: Annotated[str | None, typer.Option("--note")] = None,
        allow_agent_approval: Annotated[
            bool, typer.Option("--allow-agent-approval")
        ] = False,
        reason: Annotated[str | None, typer.Option("--reason")] = None,
        allow_empty_criteria: Annotated[
            bool, typer.Option("--allow-empty-criteria")
        ] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = approve_plan(
                state.cwd,
                task_ref,
                version=version,
                actor_type=actor,
                actor_name=actor_name,
                note=note,
                allow_agent_approval=allow_agent_approval,
                reason=reason,
                allow_empty_criteria=allow_empty_criteria,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"approved plan v{payload['plan_version']} for {payload['task_id']}",
        )

    @app.command("reject")
    def reject_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        reason: Annotated[str | None, typer.Option("--reason")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = reject_plan(state.cwd, task_ref, reason=reason)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"rejected plan for {payload['task_id']}")

    @app.command("revise")
    def revise_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = revise_plan(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"restarted planning {payload['task_id']}")
