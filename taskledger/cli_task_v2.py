from __future__ import annotations

from pathlib import Path
from typing import Annotated, cast

import typer

from taskledger.api.tasks import (
    activate_task,
    cancel_task,
    clear_active_task,
    close_task,
    create_task,
    deactivate_task,
    edit_task,
    list_task_summaries,
    show_active_task,
    show_task,
    task_dossier,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    read_text_input,
    resolve_cli_task,
)
from taskledger.errors import LaunchError


def register_task_v2_commands(app: typer.Typer) -> None:  # noqa: C901
    @app.command("create")
    def create_command(
        ctx: typer.Context,
        slug: Annotated[str, typer.Argument(..., help="Task slug.")],
        description: Annotated[
            str | None,
            typer.Option("--description", help="Task description."),
        ] = None,
        title: Annotated[
            str | None,
            typer.Option("--title", help="Task title."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = create_task(
                state.cwd,
                title=title or slug.replace("-", " ").title(),
                description=read_text_input(
                    text=description,
                    text_label="--description",
                ),
                slug=slug,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            task.to_dict(),
            human=f"created task {task.slug} ({task.id})",
        )

    @app.command("new")
    def new_command(
        ctx: typer.Context,
        title: Annotated[str, typer.Argument(..., help="Task title.")],
        description: Annotated[
            str | None,
            typer.Option("--description", help="Task description."),
        ] = None,
        slug: Annotated[str | None, typer.Option("--slug")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = create_task(
                state.cwd,
                title=title,
                description=read_text_input(
                    text=description or title,
                    text_label="--description",
                ),
                slug=slug or title,
            )
            active = activate_task(state.cwd, task.id, reason="task new")
            payload = {
                "kind": "task_new",
                "task_id": task.id,
                "task": task.to_dict(),
                "active": True,
                "active_state": active,
                "next_action": "taskledger plan start",
                "context_command": "taskledger handoff plan-context",
            }
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"created and activated {task.id}")

    @app.command("list")
    def list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = {"kind": "task_list", "tasks": list_task_summaries(state.cwd)}
        human_lines = ["TASKS"]
        if not payload["tasks"]:
            human_lines.append("(empty)")
        else:
            for task in cast(list[dict[str, object]], payload["tasks"]):
                active = task.get("active_stage")
                stage = (
                    f"{task['status_stage']} [{active}]"
                    if active
                    else str(task["status_stage"])
                )
                human_lines.append(
                    f"{task['slug']}  {task['id']}  {stage}"
                )
        emit_payload(ctx, payload, human="\n".join(human_lines))

    @app.command("active")
    def active_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_active_task(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"{payload['slug']} ({payload['task_id']})",
        )

    @app.command("activate")
    def activate_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        reason: Annotated[str | None, typer.Option("--reason")] = None,
        force: Annotated[bool, typer.Option("--force")] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = activate_task(state.cwd, ref, reason=reason, force=force)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        changed = "activated" if payload["changed"] else "already active"
        emit_payload(ctx, payload, human=f"{changed} {payload['task_id']}")

    @app.command("deactivate")
    def deactivate_command(
        ctx: typer.Context,
        reason: Annotated[str, typer.Option("--reason")],
        force: Annotated[bool, typer.Option("--force")] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = deactivate_task(state.cwd, reason=reason, force=force)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"deactivated {payload['task_id']}")

    @app.command("clear-active")
    def clear_active_command(
        ctx: typer.Context,
        reason: Annotated[str, typer.Option("--reason")],
        force: Annotated[bool, typer.Option("--force")] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = clear_active_task(state.cwd, reason=reason, force=force)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"cleared active task {payload['task_id']}")

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        json_output: Annotated[
            bool,
            typer.Option("--json", help="Render machine-readable JSON."),
        ] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            resolved = resolve_cli_task(state.cwd, ref)
            payload = show_task(state.cwd, resolved.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        task = payload["task"]
        assert isinstance(task, dict)
        if json_output and not state.json_output:
            from taskledger.cli_common import render_json

            typer.echo(render_json({"ok": True, **payload, "result": payload}))
        else:
            emit_payload(
                ctx,
                payload,
                human=(
                    f"{task['title']} ({task['id']})\n"
                    f"status: {task['status_stage']}\n"
                    f"active_stage: {task.get('active_stage') or 'none'}\n"
                    f"slug: {task['slug']}"
                ),
            )

    @app.command("edit")
    def edit_command(
        ctx: typer.Context,
        ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        title: Annotated[str | None, typer.Option("--title")] = None,
        description: Annotated[str | None, typer.Option("--description")] = None,
        from_file: Annotated[Path | None, typer.Option("--from-file")] = None,
        priority: Annotated[str | None, typer.Option("--priority")] = None,
        owner: Annotated[str | None, typer.Option("--owner")] = None,
        add_label: Annotated[list[str] | None, typer.Option("--add-label")] = None,
        remove_label: Annotated[
            list[str] | None,
            typer.Option("--remove-label"),
        ] = None,
        add_note: Annotated[list[str] | None, typer.Option("--add-note")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, ref)
            task = edit_task(
                state.cwd,
                task.id,
                title=title,
                description=(
                    read_text_input(text=description, from_file=from_file)
                    if description is not None or from_file is not None
                    else None
                ),
                priority=priority,
                owner=owner,
                add_labels=tuple(add_label or ()),
                remove_labels=tuple(remove_label or ()),
                add_notes=tuple(add_note or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"updated task {task.id}")

    @app.command("cancel")
    def cancel_command(
        ctx: typer.Context,
        ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        reason: Annotated[str | None, typer.Option("--reason")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, ref)
            payload = cancel_task(state.cwd, task.id, reason=reason)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"cancelled task {payload['task_id']}")

    @app.command("close")
    def close_command(
        ctx: typer.Context,
        ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, ref)
            payload = close_task(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"closed task {payload['task_id']}")

    @app.command("dossier")
    def dossier_command(
        ctx: typer.Context,
        ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        format_name: Annotated[str, typer.Option("--format")] = "markdown",
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, ref)
            payload = task_dossier(state.cwd, task.id, format_name=format_name)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=payload if isinstance(payload, str) else None)
