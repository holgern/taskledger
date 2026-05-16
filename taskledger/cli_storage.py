from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.storage import (
    storage_move,
    storage_where,
    sync_commit,
    sync_preflight,
    sync_status,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
)
from taskledger.errors import LaunchError


def _render_storage_where(payload: dict[str, object]) -> str:
    lines = [
        f"Workspace: {payload['workspace_root']}",
        f"Config: {payload['config_path']}",
        f"Storage: {payload['taskledger_dir']}",
        (
            f"Project: {payload['project_name']} "
            f"({payload['project_uuid'] or 'no project_uuid'})"
        ),
        f"Ledger: {payload['ledger_ref']}",
        f"Inside workspace: {'yes' if payload['inside_workspace'] else 'no'}",
        f"Git repo: {payload['git_root'] or 'no'}",
        f"Active locks: {payload['active_lock_count']}",
    ]
    warnings = payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings if isinstance(item, str))
    return "\n".join(lines)


def _render_sync_preflight(payload: dict[str, object]) -> str:
    location = payload["location"]
    assert isinstance(location, dict)
    lines = [
        f"Storage: {location['taskledger_dir']}",
        f"Exists: {'yes' if payload['taskledger_dir_exists'] else 'no'}",
        f"Doctor: {'healthy' if payload['doctor_healthy'] else 'issues found'}",
        f"Active locks: {location['active_lock_count']}",
        (
            "Tracked in workspace Git: "
            f"{'yes' if payload['tracked_in_workspace_git'] else 'no'}"
        ),
    ]
    git_status_lines = payload.get("git_status_lines", [])
    if isinstance(git_status_lines, list) and git_status_lines:
        lines.append("Git status:")
        lines.extend(str(item) for item in git_status_lines)
    warnings = payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings if isinstance(item, str))
    return "\n".join(lines)


def _render_storage_move(payload: dict[str, object]) -> str:
    lines = [
        f"{str(payload['mode']).capitalize()}d storage to {payload['target']}",
        f"Config: {payload['config_path']}",
        f"Source: {payload['source']}",
    ]
    backup_path = payload.get("backup_path")
    if isinstance(backup_path, str) and backup_path:
        lines.append(f"Backup: {backup_path}")
    next_commands = payload.get("next_commands", [])
    if isinstance(next_commands, list) and next_commands:
        lines.append("Next:")
        lines.extend(f"- {item}" for item in next_commands if isinstance(item, str))
    warnings = payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings if isinstance(item, str))
    return "\n".join(lines)


def _render_sync_status(payload: dict[str, object]) -> str:
    lines = [
        f"Storage: {payload['taskledger_dir']}",
        f"Git repo: {payload['git_root'] or 'no'}",
        f"Active locks: {payload['active_lock_count']}",
    ]
    status_lines = payload.get("status_lines", [])
    if isinstance(status_lines, list) and status_lines:
        lines.append("Git status:")
        lines.extend(str(item) for item in status_lines)
    else:
        lines.append("Git status: clean")
    warnings = payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings if isinstance(item, str))
    return "\n".join(lines)


def _render_sync_commit(payload: dict[str, object]) -> str:
    lines = [
        f"Committed storage repo at {payload['git_root']}",
        f"Commit: {payload['commit']}",
        f"Path: {payload['relative_path']}",
    ]
    warnings = payload.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings if isinstance(item, str))
    return "\n".join(lines)


def register_storage_commands(app: typer.Typer) -> None:
    @app.command("where")
    def where_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = storage_where(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            result_type="storage_where",
            human=_render_storage_where(payload),
        )

    @app.command("move")
    def move_command(
        ctx: typer.Context,
        to: Annotated[str, typer.Option("--to", help="New taskledger_dir target.")],
        mode: Annotated[
            str,
            typer.Option("--mode", help="Migration mode: copy or move."),
        ] = "move",
        adopt_existing: Annotated[
            bool,
            typer.Option("--adopt-existing", help="Adopt a non-empty existing target."),
        ] = False,
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                help="Allow migration from an already external taskledger_dir.",
            ),
        ] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = storage_move(
                state.cwd,
                target=Path(to),
                mode=mode,
                adopt_existing=adopt_existing,
                force=force,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            result_type="storage_move",
            human=_render_storage_move(payload),
        )


def register_sync_commands(app: typer.Typer) -> None:
    @app.command("preflight")
    def preflight_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = sync_preflight(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            result_type="sync_preflight",
            human=_render_sync_preflight(payload),
        )

    @app.command("status")
    def status_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = sync_status(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            result_type="sync_status",
            human=_render_sync_status(payload),
        )

    @app.command("commit")
    def commit_command(
        ctx: typer.Context,
        message: Annotated[
            str,
            typer.Option(
                "--message",
                help="Commit message for storage state.",
            ),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = sync_commit(state.cwd, message=message)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            result_type="sync_commit",
            human=_render_sync_commit(payload),
        )
