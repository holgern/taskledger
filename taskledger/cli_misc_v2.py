from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.handoff import render_handoff
from taskledger.api.introductions import (
    create_introduction,
    link_introduction,
    list_introductions,
    resolve_introduction,
)
from taskledger.api.locks import break_lock, list_locks, show_lock
from taskledger.api.tasks import (
    add_file_link,
    add_requirement,
    add_todo,
    can_perform,
    list_file_links,
    next_action,
    reindex,
    remove_file_link,
    remove_requirement,
    set_todo_done,
    show_todo,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    read_text_input,
)
from taskledger.errors import LaunchError
from taskledger.services.doctor_v2 import inspect_v2_locks, inspect_v2_project
from taskledger.storage.v2 import resolve_task


def register_todo_v2_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        text: Annotated[str, typer.Option("--text")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = add_todo(state.cwd, task_ref, text=text)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"added todo on {task.id}")

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_task(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = [todo.to_dict() for todo in task.todos]
        lines = ["TODOS"]
        for todo in task.todos:
            status = "done" if todo.done else "open"
            lines.append(f"{todo.id}  {status}  {todo.text}")
        emit_payload(
            ctx,
            payload,
            human="\n".join(lines) if payload else "TODOS\n(empty)",
        )

    @app.command("done")
    def done_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        todo_id: Annotated[str, typer.Argument(...)],
    ) -> None:
        _emit_todo_update(ctx, task_ref, todo_id, done=True)

    @app.command("undone")
    def undone_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        todo_id: Annotated[str, typer.Argument(...)],
    ) -> None:
        _emit_todo_update(ctx, task_ref, todo_id, done=False)

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        todo_id: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_todo(state.cwd, task_ref, todo_id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        todo = payload["todo"]
        assert isinstance(todo, dict)
        emit_payload(ctx, payload, human=f"{todo['id']}  {todo['text']}")


def register_intro_v2_commands(app: typer.Typer) -> None:
    @app.command("create")
    def create_command(
        ctx: typer.Context,
        title: Annotated[str, typer.Argument(...)],
        text: Annotated[str | None, typer.Option("--text")] = None,
        from_file: Annotated[Path | None, typer.Option("--from-file")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            intro = create_introduction(
                state.cwd,
                title=title,
                body=read_text_input(text=text, from_file=from_file),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, intro.to_dict(), human=f"created intro {intro.id}")

    @app.command("list")
    def list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = [intro.to_dict() for intro in list_introductions(state.cwd)]
        human = "\n".join(
            ["INTRODUCTIONS", *[f"{intro['id']}  {intro['slug']}" for intro in payload]]
        )
        emit_payload(
            ctx,
            payload,
            human=human if payload else "INTRODUCTIONS\n(empty)",
        )

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        intro_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            intro = resolve_introduction(state.cwd, intro_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, intro.to_dict(), human=intro.body)

    @app.command("link")
    def link_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        intro_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = link_introduction(state.cwd, task_ref, intro_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"linked intro to {task.id}")


def register_file_v2_commands(app: typer.Typer) -> None:
    @app.command("link")
    def link_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "code",
        label: Annotated[str | None, typer.Option("--label")] = None,
        required_for_validation: Annotated[
            bool,
            typer.Option("--required-for-validation"),
        ] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = add_file_link(
                state.cwd,
                task_ref,
                path=path,
                kind=kind,
                label=label,
                required_for_validation=required_for_validation,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"linked file on {task.id}")

    @app.command("unlink")
    def unlink_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        path: Annotated[str, typer.Option("--path")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = remove_file_link(state.cwd, task_ref, path=path)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"unlinked file on {task.id}")

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = list_file_links(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        file_links = payload["file_links"]
        assert isinstance(file_links, list)
        lines = ["FILES"]
        for item in file_links:
            if isinstance(item, dict):
                lines.append(f"@{item.get('path')} [{item.get('kind')}]")
        emit_payload(
            ctx, payload, human="\n".join(lines) if file_links else "FILES\n(empty)"
        )


def register_require_v2_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        required_task_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = add_requirement(state.cwd, task_ref, required_task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"added requirement on {task.id}")

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_task(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            list(task.requirements),
            human="\n".join(["REQUIREMENTS", *task.requirements])
            if task.requirements
            else "REQUIREMENTS\n(empty)",
        )

    @app.command("remove")
    def remove_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        required_task_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = remove_requirement(state.cwd, task_ref, required_task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"removed requirement on {task.id}")


def register_lock_v2_commands(app: typer.Typer) -> None:
    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = show_lock(state.cwd, task_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=str(payload["lock"]))

    @app.command("break")
    def break_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        reason: Annotated[str, typer.Option("--reason")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = break_lock(state.cwd, task_ref, reason=reason)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"broke lock for {payload['task_id']}")

    @app.command("list")
    def list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = list_locks(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        locks = payload["locks"]
        assert isinstance(locks, list)
        lines = ["LOCKS"]
        for item in locks:
            if isinstance(item, dict):
                lines.append(
                    f"{item.get('task_id')}  {item.get('stage')}  {item.get('run_id')}"
                )
        emit_payload(
            ctx, payload, human="\n".join(lines) if locks else "LOCKS\n(empty)"
        )


def register_handoff_v2_commands(app: typer.Typer) -> None:
    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        format_name: Annotated[str, typer.Option("--format")] = "text",
    ) -> None:
        _emit_handoff(ctx, task_ref, mode="show", format_name=format_name)

    @app.command("plan-context")
    def plan_context_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        format_name: Annotated[str, typer.Option("--format")] = "text",
    ) -> None:
        _emit_handoff(ctx, task_ref, mode="plan-context", format_name=format_name)

    @app.command("implementation-context")
    def implementation_context_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        format_name: Annotated[str, typer.Option("--format")] = "text",
    ) -> None:
        _emit_handoff(
            ctx,
            task_ref,
            mode="implementation-context",
            format_name=format_name,
        )

    @app.command("validation-context")
    def validation_context_command(
        ctx: typer.Context,
        task_ref: Annotated[str, typer.Argument(...)],
        format_name: Annotated[str, typer.Option("--format")] = "text",
    ) -> None:
        _emit_handoff(
            ctx,
            task_ref,
            mode="validation-context",
            format_name=format_name,
        )


def emit_next_action_command(
    ctx: typer.Context,
    task_ref: str,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        payload = next_action(state.cwd, task_ref)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, payload, human=f"{payload['action']}: {payload['reason']}")


def emit_can_command(ctx: typer.Context, task_ref: str, action: str) -> None:
    state = cli_state_from_context(ctx)
    try:
        payload = can_perform(state.cwd, task_ref, action)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    prefix = "yes" if payload["ok"] else "no"
    emit_payload(ctx, payload, human=f"{prefix}: {payload['reason']}")


def emit_reindex_command(ctx: typer.Context) -> None:
    state = cli_state_from_context(ctx)
    payload = reindex(state.cwd)
    emit_payload(ctx, payload, human="reindexed v2 task state")


def emit_doctor_command(ctx: typer.Context) -> None:
    state = cli_state_from_context(ctx)
    payload = inspect_v2_project(state.cwd)
    emit_payload(
        ctx,
        payload,
        human=f"healthy: {payload['healthy']} errors: {len(payload['errors'])}",
    )


def emit_doctor_locks_command(ctx: typer.Context) -> None:
    state = cli_state_from_context(ctx)
    payload = inspect_v2_locks(state.cwd)
    emit_payload(
        ctx,
        payload,
        human=_expired_locks_human(payload["expired_locks"]),
    )


def _emit_todo_update(
    ctx: typer.Context,
    task_ref: str,
    todo_id: str,
    *,
    done: bool,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = set_todo_done(state.cwd, task_ref, todo_id, done=done)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, task.to_dict(), human=f"updated todo {todo_id}")


def _emit_handoff(
    ctx: typer.Context,
    task_ref: str,
    *,
    mode: str,
    format_name: str,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        payload = render_handoff(
            state.cwd,
            task_ref,
            mode=mode,
            format_name=format_name,
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, payload, human=payload if isinstance(payload, str) else None)


def _expired_locks_human(payload: object) -> str:
    if not isinstance(payload, list) or not payload:
        return "EXPIRED LOCKS\n(empty)"
    lines = ["EXPIRED LOCKS"]
    for item in payload:
        if isinstance(item, dict):
            lines.append(str(item.get("task_id")))
    return "\n".join(lines)
