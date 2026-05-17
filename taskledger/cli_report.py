from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.cli_common import (
    TaskRefArgument,
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    resolve_cli_task,
    write_text_output,
)
from taskledger.errors import LaunchError
from taskledger.services.html_reports import (
    HtmlReportOptions,
    HtmlSiteOptions,
    render_task_report_html,
    write_html_site,
)


def report_html_command(
    ctx: typer.Context,
    task_arg: TaskRefArgument = None,
    active: Annotated[
        bool,
        typer.Option("--active", help="Render the active task report."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Write report HTML to file."),
    ] = None,
    preset: Annotated[str, typer.Option("--preset")] = "full",
    section: Annotated[
        list[str] | None,
        typer.Option("--section", help="Render only this section. Repeatable."),
    ] = None,
    include: Annotated[
        list[str] | None,
        typer.Option("--include", help="Add a section. Repeatable."),
    ] = None,
    without: Annotated[
        list[str] | None,
        typer.Option("--without", help="Remove a section. Repeatable."),
    ] = None,
    events_limit: Annotated[int, typer.Option("--events-limit")] = 50,
    command_log_limit: Annotated[int, typer.Option("--command-log-limit")] = 100,
    include_command_output: Annotated[
        bool,
        typer.Option("--include-command-output/--no-include-command-output"),
    ] = False,
    include_empty: Annotated[
        bool,
        typer.Option("--include-empty/--no-include-empty"),
    ] = True,
    refresh_seconds: Annotated[
        int | None,
        typer.Option("--refresh-seconds"),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        if task_arg and active and task_arg != "active":
            raise LaunchError(
                "TASK_REF and --active are mutually exclusive.",
                code="USAGE_ERROR",
                exit_code=2,
            )
        if not task_arg and not active:
            raise LaunchError(
                "TASK_REF or --active is required.",
                code="USAGE_ERROR",
                exit_code=2,
            )
        if output is None:
            raise LaunchError(
                "--output is required.",
                code="USAGE_ERROR",
                exit_code=2,
            )

        if active or task_arg == "active":
            task = resolve_cli_task(state.cwd, None)
        else:
            task = resolve_cli_task(state.cwd, task_arg)

        rendered = render_task_report_html(
            state.cwd,
            task.id,
            options=HtmlReportOptions(
                preset=preset,
                sections=tuple(section or ()),
                include_sections=tuple(include or ()),
                exclude_sections=tuple(without or ()),
                events_limit=events_limit,
                command_log_limit=command_log_limit,
                include_command_output=include_command_output,
                include_empty=include_empty,
                refresh_seconds=refresh_seconds,
                mode="static",
            ),
        )
        content = rendered["content"]
        assert isinstance(content, str)
        written = write_text_output(output, content)
        payload = {
            "kind": "html_task_report_written",
            "task_id": rendered["task_id"],
            "output_path": str(written),
            "refresh_seconds": rendered["refresh_seconds"],
            "sections": rendered["sections"],
        }
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(
        ctx,
        payload,
        human=(
            f"wrote HTML task report {payload['task_id']} to {payload['output_path']}"
        ),
    )


def report_site_command(
    ctx: typer.Context,
    output: Annotated[
        Path,
        typer.Option("-o", "--output", help="Write report site to directory."),
    ],
    include_archived: Annotated[
        bool,
        typer.Option("--include-archived", help="Include archived tasks."),
    ] = False,
    refresh_seconds: Annotated[
        int | None,
        typer.Option("--refresh-seconds"),
    ] = None,
    preset: Annotated[str, typer.Option("--preset")] = "full",
) -> None:
    state = cli_state_from_context(ctx)
    try:
        payload = write_html_site(
            state.cwd,
            output,
            options=HtmlSiteOptions(
                include_archived=include_archived,
                refresh_seconds=refresh_seconds,
                preset=preset,
            ),
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(
        ctx,
        payload,
        human=(
            f"wrote HTML report site to {payload['output_dir']} "
            f"({payload['task_count']} task pages)"
        ),
    )


def register_report_commands(app: typer.Typer) -> None:
    app.command("html")(report_html_command)
    app.command("site")(report_site_command)
