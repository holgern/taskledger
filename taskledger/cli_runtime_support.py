from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

import typer

from taskledger.api.runtime_support import (
    create_run_artifact_layout,
    get_effective_project_config,
    resolve_repo_root,
)
from taskledger.cli_common import cli_state_from_context, emit_error, emit_payload
from taskledger.errors import LaunchError


def register_runtime_support_commands(app: typer.Typer) -> None:
    @app.command("config")
    def runtime_support_config_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = asdict(get_effective_project_config(state.cwd))
        emit_payload(ctx, payload, human="loaded runtime support config")

    @app.command("run-layout")
    def runtime_support_run_layout_command(
        ctx: typer.Context,
        origin: Annotated[
            str,
            typer.Option("--origin", help="Origin label for the run artifacts."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            layout = create_run_artifact_layout(state.cwd, origin=origin)
        except ValueError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {
                "run_dir": layout.run_dir,
                "metadata_file": layout.metadata_file,
                "report_file": layout.report_file,
                "result_file": layout.result_file,
            },
            human=f"created run artifact layout: {layout.run_dir}",
        )

    @app.command("resolve-repo")
    def runtime_support_resolve_repo_command(
        ctx: typer.Context,
        repo_ref: Annotated[str, typer.Argument(..., help="Repo ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            root = resolve_repo_root(state.cwd, repo_ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"repo_ref": repo_ref, "root": str(root)},
            human=f"resolved repo {repo_ref}: {root}",
        )
