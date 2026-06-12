from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.changelog import (
    build_changelog_section,
    render_changelog_section,
    update_changelog_file,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
)
from taskledger.errors import LaunchError


def register_build_command(app: typer.Typer) -> None:
    @app.command("build")
    def build_command(
        ctx: typer.Context,
        version: Annotated[str, typer.Argument(..., help="Release version to build.")],
        release_date: Annotated[
            str,
            typer.Option("--release-date", help="Release date (YYYY-MM-DD)."),
        ],
        since_version: Annotated[str | None, typer.Option("--since")] = None,
        since_task: Annotated[str | None, typer.Option("--since-task")] = None,
        from_task: Annotated[str | None, typer.Option("--from-task")] = None,
        until_task: Annotated[str | None, typer.Option("--until-task")] = None,
        target_file: Annotated[Path, typer.Option("--target-file")] = Path(
            "CHANGELOG.md"
        ),
        dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
        replace: Annotated[bool, typer.Option("--replace")] = False,
        include_draft: Annotated[bool, typer.Option("--include-draft")] = False,
        strict: Annotated[bool, typer.Option("--strict/--no-strict")] = True,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = build_changelog_section(
                state.cwd,
                version=version,
                release_date=release_date,
                since_version=since_version,
                since_task=since_task,
                from_task=from_task,
                until_task=until_task,
                include_draft=include_draft,
                strict=strict,
            )
            section = render_changelog_section(payload)
            payload["target_file"] = str(target_file)
            payload["dry_run"] = dry_run
            if dry_run:
                payload["written"] = False
                if state.json_output:
                    emit_payload(ctx, payload, result_type="changelog_build")
                    return
                typer.echo(section, nl=False)
                return
            write_result = update_changelog_file(
                (state.cwd / target_file).resolve(),
                section=section,
                version=version,
                replace=replace,
            )
            payload.update(write_result)
            emit_payload(
                ctx,
                payload,
                result_type="changelog_build",
                human=(f"updated {target_file} with changelog section for v{version}"),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
