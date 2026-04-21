from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.runs import list_runs, show_run
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_runs_commands(app: typer.Typer) -> None:
    @app.command("list")
    def runs_list_command(
        ctx: typer.Context,
        limit: Annotated[
            int | None,
            typer.Option("--limit", help="Limit the number of runs shown."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        runs = list_runs(state.cwd, limit=limit)
        emit_payload(
            ctx,
            [run.to_dict() for run in runs],
            human=human_list(
                "RUNS",
                [
                    f"{run.run_id}  {run.status}  {run.origin or '-'}"
                    for run in runs
                ],
            ),
        )

    @app.command("show")
    def runs_show_command(
        ctx: typer.Context,
        run_id: Annotated[str, typer.Argument(..., help="Run id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            run = show_run(state.cwd, run_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            run.to_dict(),
            human=human_kv(
                f"RUN {run.run_id}",
                [
                    ("status", run.status),
                    ("origin", run.origin),
                    ("project_item_ref", run.project_item_ref),
                    ("result_path", run.result_path),
                ],
            ),
        )
