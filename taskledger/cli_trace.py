from __future__ import annotations

from typing import Annotated

import typer

from taskledger.cli_common import cli_state_from_context, emit_payload, render_json
from taskledger.errors import LaunchError
from taskledger.services.trace import build_task_trace


def register_trace_command(app: typer.Typer) -> None:
    @app.command("trace")
    def trace_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(help="Task id or slug to trace.")],
        format: Annotated[
            str, typer.Option("--format", "-f", help="Output format: json.")
        ] = "json",
    ) -> None:
        """Emit a read-only task-centered trace bundle."""
        if format != "json":
            raise LaunchError("Only --format json is supported for trace.")
        state = cli_state_from_context(ctx)
        payload = build_task_trace(state.cwd, task_ref)
        if format == "json":
            typer.echo(render_json(payload))
            return
        emit_payload(ctx, payload)
