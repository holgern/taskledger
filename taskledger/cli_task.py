from __future__ import annotations

from pathlib import Path
from typing import Annotated, cast

import typer

from taskledger.api.tasks import (
    activate_task,
    cancel_task,
    close_task,
    create_follow_up_task,
    create_task,
    deactivate_task,
    edit_task,
    list_task_summaries,
    show_active_task,
    show_task,
    task_dossier,
)
from taskledger.cli_common import (
    TaskOption,
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    read_text_input,
    resolve_cli_task,
)
from taskledger.errors import LaunchError
from taskledger.services.tasks import list_events as _list_events


def register_task_v2_commands(app: typer.Typer) -> None:  # noqa: C901
    @app.command("create")
    def create_command(
        ctx: typer.Context,
        title_arg: Annotated[str, typer.Argument(..., help="Task title.")],
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
                title=title_arg,
                description=read_text_input(
                    text=description or title_arg,
                    text_label="--description",
                ),
                slug=slug or title_arg,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            task.to_dict(),
            human=f"created task {task.slug} ({task.id})",
        )

    @app.command("follow-up")
    def follow_up_command(
        ctx: typer.Context,
        parent_ref: Annotated[
            str,
            typer.Argument(..., help="Completed parent task ref."),
        ],
        title: Annotated[
            str,
            typer.Argument(..., help="Follow-up task title."),
        ],
        description: Annotated[
            str | None,
            typer.Option("--description", help="Follow-up task description."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read description from a file."),
        ] = None,
        slug: Annotated[str | None, typer.Option("--slug")] = None,
        activate: Annotated[bool, typer.Option("--activate/--no-activate")] = False,
        copy_files: Annotated[
            bool, typer.Option("--copy-files/--no-copy-files")
        ] = False,
        copy_links: Annotated[
            bool, typer.Option("--copy-links/--no-copy-links")
        ] = False,
        label: Annotated[list[str] | None, typer.Option("--label")] = None,
        reason: Annotated[str | None, typer.Option("--reason")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = create_follow_up_task(
                state.cwd,
                parent_ref,
                title=title,
                description=(
                    read_text_input(text=description, from_file=from_file)
                    if description is not None or from_file is not None
                    else None
                ),
                slug=slug,
                labels=tuple(label or ()),
                activate=activate,
                copy_files=copy_files,
                copy_links=copy_links,
                reason=reason,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        task_id = payload["task_id"]
        parent_task_id = payload["parent_task_id"]
        next_command = payload["next_command"]
        assert isinstance(task_id, str)
        assert isinstance(parent_task_id, str)
        assert isinstance(next_command, str)
        lead = (
            f"created and activated follow-up task {task_id} for {parent_task_id}"
            if payload["activated"]
            else f"created follow-up task {task_id} for {parent_task_id}"
        )
        emit_payload(ctx, payload, human=f"{lead}\nnext: {next_command}")

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
                human_lines.append(f"{task['slug']}  {task['id']}  {stage}")
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

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            resolved = resolve_cli_task(state.cwd, task_ref)
            payload = show_task(state.cwd, resolved.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        task = payload["task"]
        assert isinstance(task, dict)
        human_lines = [
            f"{task['title']} ({task['id']})",
            f"status: {task['status_stage']}",
            f"active_stage: {task.get('active_stage') or 'none'}",
            f"slug: {task['slug']}",
        ]
        parent_task = payload.get("parent_task")
        if isinstance(parent_task, dict):
            human_lines.append(
                f"follow-up of: {parent_task['task_id']} {parent_task['title']}"
            )
        follow_up_tasks = payload.get("follow_up_tasks")
        if isinstance(follow_up_tasks, list) and follow_up_tasks:
            rendered = ", ".join(
                f"{item['task_id']} {item['title']}"
                for item in follow_up_tasks
                if isinstance(item, dict)
            )
            if rendered:
                human_lines.append(f"follow-ups: {rendered}")
        emit_payload(
            ctx,
            payload,
            human="\n".join(human_lines),
        )

    @app.command("edit")
    def edit_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
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
            task = resolve_cli_task(state.cwd, task_ref)
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
        task_ref: TaskOption = None,
        reason: Annotated[str | None, typer.Option("--reason")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = cancel_task(state.cwd, task.id, reason=reason)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"cancelled task {payload['task_id']}")

    @app.command("close")
    def close_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        note: Annotated[str | None, typer.Option("--note")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = close_task(state.cwd, task.id, note=note)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"closed task {payload['task_id']}")

    @app.command("events")
    def events_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        all_tasks: Annotated[
            bool, typer.Option("--all", help="Show events for all tasks.")
        ] = False,
        limit: Annotated[int, typer.Option("--limit", help="Max events to show.")] = 50,
    ) -> None:
        state = cli_state_from_context(ctx)
        events = _list_events(state.cwd)
        if not all_tasks:
            try:
                resolved = resolve_cli_task(state.cwd, task_ref)
            except LaunchError as exc:
                emit_error(ctx, exc)
                raise typer.Exit(code=launch_error_exit_code(exc)) from exc
            events = [e for e in events if e.get("task_id") == resolved.id]
        events = events[-limit:]
        payload = {"kind": "event_list", "items": events}
        from taskledger.cli_common import render_events_human

        human = render_events_human(events)
        emit_payload(ctx, payload, human=human, result_type="event_list")

    @app.command("dossier")
    def dossier_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        format_name: Annotated[str, typer.Option("--format")] = "markdown",
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = task_dossier(state.cwd, task.id, format_name=format_name)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=payload if isinstance(payload, str) else None)
