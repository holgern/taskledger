from __future__ import annotations

from typing import Annotated, cast

import typer

from taskledger.api.releases import (
    list_release_records,
    show_release,
    tag_release,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    launch_error_exit_code,
)
from taskledger.errors import LaunchError


def register_release_commands(app: typer.Typer) -> None:
    @app.command("tag")
    def tag_command(
        ctx: typer.Context,
        version: Annotated[str, typer.Argument(..., help="Release version.")],
        at_task: Annotated[str, typer.Option("--at-task", help="Boundary task ref.")],
        note: Annotated[str | None, typer.Option("--note")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = tag_release(
                state.cwd,
                version=version,
                at_task=at_task,
                note=note,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        release = cast(dict[str, object], payload["release"])
        emit_payload(
            ctx,
            payload,
            human=(f"tagged release {version} at {release['boundary_task_id']}"),
        )

    @app.command("list")
    def list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = {"kind": "release_list", "releases": list_release_records(state.cwd)}
        human_lines = ["RELEASES"]
        releases = cast(list[dict[str, object]], payload["releases"])
        if not releases:
            human_lines.append("(empty)")
        else:
            for release in releases:
                note = release.get("note")
                suffix = f"  {note}" if isinstance(note, str) and note else ""
                human_lines.append(
                    f"{release['version']}  {release['boundary_task_id']}  "
                    f"{release['created_at']}{suffix}"
                )
        emit_payload(ctx, payload, human="\n".join(human_lines))

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        version: Annotated[str, typer.Argument(..., help="Release version.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_release(state.cwd, version)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        release = cast(dict[str, object], payload["release"])
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                f"RELEASE {release['version']}",
                [
                    ("boundary_task_id", release.get("boundary_task_id")),
                    ("created_at", release.get("created_at")),
                    ("previous_version", release.get("previous_version")),
                    ("task_count", release.get("task_count")),
                    ("note", release.get("note")),
                ],
            ),
        )
