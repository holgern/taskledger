from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.runs import (
    apply_run_result,
    cleanup_run_records,
    delete_run_entry,
    list_runs,
    promote_run_output,
    promote_run_report,
    show_run,
    summarize_run_inventory,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_runs_commands(app: typer.Typer) -> None:
    @app.command("apply")
    def runs_apply_command(
        ctx: typer.Context,
        run_id: Annotated[str, typer.Argument(..., help="Run id.")],
        mode: Annotated[
            str,
            typer.Option("--as", help="Promotion mode: output or report."),
        ] = "output",
        mark_stage_succeeded: Annotated[
            bool,
            typer.Option(
                "--mark-stage-succeeded",
                help="Mark the related workflow stage succeeded.",
            ),
        ] = False,
        summary: Annotated[
            str | None,
            typer.Option("--summary", help="Optional stage completion summary."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = apply_run_result(
                state.cwd,
                run_id,
                mode=mode,
                mark_stage_succeeded=mark_stage_succeeded,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            payload,
            human=f"applied run {payload['run']['id']} as {payload['applied']['mode']}",
        )

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

    @app.command("delete")
    def runs_delete_command(
        ctx: typer.Context,
        run_id: Annotated[str, typer.Argument(..., help="Run id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            run = delete_run_entry(state.cwd, run_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            run.to_dict(),
            human=f"deleted run {run.run_id}",
        )

    @app.command("cleanup")
    def runs_cleanup_command(
        ctx: typer.Context,
        keep: Annotated[
            int,
            typer.Option("--keep", help="Number of newest runs to keep."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            removed = cleanup_run_records(state.cwd, keep=keep)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            [run.to_dict() for run in removed],
            human=human_list(
                "REMOVED RUNS",
                [f"{run.run_id}  {run.status}" for run in removed],
            ),
        )

    @app.command("promote-output")
    def runs_promote_output_command(
        ctx: typer.Context,
        run_id: Annotated[str, typer.Argument(..., help="Run id.")],
        name: Annotated[str, typer.Option("--name", help="Memory name.")],
    ) -> None:
        _emit_promoted_run_memory(
            ctx,
            run_id,
            name=name,
            promote_func=promote_run_output,
            label="output",
        )

    @app.command("promote-report")
    def runs_promote_report_command(
        ctx: typer.Context,
        run_id: Annotated[str, typer.Argument(..., help="Run id.")],
        name: Annotated[str, typer.Option("--name", help="Memory name.")],
    ) -> None:
        _emit_promoted_run_memory(
            ctx,
            run_id,
            name=name,
            promote_func=promote_run_report,
            label="report",
        )

    @app.command("summary")
    def runs_summary_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = summarize_run_inventory(state.cwd)
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                "RUN SUMMARY",
                [
                    ("count", payload["count"]),
                    ("by_status", _format_counts(payload["by_status"])),
                    ("by_origin", _format_counts(payload["by_origin"])),
                ],
            ),
        )


def _emit_promoted_run_memory(
    ctx: typer.Context,
    run_id: str,
    *,
    name: str,
    promote_func,
    label: str,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        run, memory = promote_func(state.cwd, run_id, name=name)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(
        ctx,
        {"run": run.to_dict(), "memory": memory.to_dict()},
        human=f"promoted run {run.run_id} {label} to memory {memory.id}",
    )


def _format_counts(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    return ", ".join(f"{key}={count}" for key, count in sorted(value.items()))
