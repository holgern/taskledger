from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.tasks import (
    cancel_task,
    close_task,
    create_task,
    edit_task,
    list_task_summaries,
    show_task,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    read_text_input,
)
from taskledger.errors import LaunchError


def register_task_v2_commands(app: typer.Typer) -> None:
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

    @app.command("list")
    def list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = {"kind": "task_list", "tasks": list_task_summaries(state.cwd)}
        human_lines = ["TASKS"]
        if not payload["tasks"]:
            human_lines.append("(empty)")
        else:
            for task in payload["tasks"]:
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

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_task(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        task = payload["task"]
        assert isinstance(task, dict)
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
        ref: Annotated[str, typer.Argument(..., help="Task ref.")],
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
            task = edit_task(
                state.cwd,
                ref,
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
        ref: Annotated[str, typer.Argument(..., help="Task ref.")],
        reason: Annotated[str | None, typer.Option("--reason")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = cancel_task(state.cwd, ref, reason=reason)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"cancelled task {payload['task_id']}")

    @app.command("close")
    def close_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Task ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = close_task(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"closed task {payload['task_id']}")
