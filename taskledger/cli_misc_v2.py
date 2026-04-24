from __future__ import annotations

from pathlib import Path
from typing import Annotated, cast

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
    waive_requirement,
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
from taskledger.services.doctor_v2 import (
    inspect_v2_indexes,
    inspect_v2_locks,
    inspect_v2_project,
    inspect_v2_schema,
)
from taskledger.storage.v2 import load_requirements, load_todos


def register_todo_v2_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        text: Annotated[str, typer.Option("--text")],
        mandatory: Annotated[
            bool,
            typer.Option("--mandatory", help="Mark todo as mandatory gate."),
        ] = False,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            task = add_todo(state.cwd, task.id, text=text, mandatory=mandatory)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"added todo on {task.id}")

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            todos = load_todos(state.cwd, task.id).todos
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = [todo.to_dict() for todo in todos]
        lines = ["TODOS"]
        for todo in todos:
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
        todo_id: Annotated[str, typer.Argument(...)],
        legacy_todo_id: Annotated[str | None, typer.Argument(help="Todo id.")] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        target_ref, resolved_todo_id = _split_legacy_secondary_ref(
            task_ref,
            todo_id,
            legacy_todo_id,
        )
        _emit_todo_update(ctx, target_ref, resolved_todo_id, done=True)

    @app.command("undone")
    def undone_command(
        ctx: typer.Context,
        todo_id: Annotated[str, typer.Argument(...)],
        legacy_todo_id: Annotated[str | None, typer.Argument(help="Todo id.")] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        target_ref, resolved_todo_id = _split_legacy_secondary_ref(
            task_ref,
            todo_id,
            legacy_todo_id,
        )
        _emit_todo_update(ctx, target_ref, resolved_todo_id, done=False)

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        todo_id: Annotated[str, typer.Argument(...)],
        legacy_todo_id: Annotated[str | None, typer.Argument(help="Todo id.")] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            target_ref, resolved_todo_id = _split_legacy_secondary_ref(
                task_ref,
                todo_id,
                legacy_todo_id,
            )
            task = resolve_cli_task(state.cwd, target_ref)
            payload = show_todo(state.cwd, task.id, resolved_todo_id)
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
        intro_ref: Annotated[str, typer.Argument(...)],
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            task = link_introduction(state.cwd, task.id, intro_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"linked intro to {task.id}")


def register_file_v2_commands(app: typer.Typer) -> None:
    @app.command("link")
    def link_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "code",
        label: Annotated[str | None, typer.Option("--label")] = None,
        required_for_validation: Annotated[
            bool,
            typer.Option("--required-for-validation"),
        ] = False,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            task = add_file_link(
                state.cwd,
                task.id,
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
        path: Annotated[str, typer.Option("--path")],
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            task = remove_file_link(state.cwd, task.id, path=path)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"unlinked file on {task.id}")

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            payload = list_file_links(state.cwd, task.id)
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


def register_link_v2_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "code",
        label: Annotated[str | None, typer.Option("--label")] = None,
        required_for_validation: Annotated[
            bool,
            typer.Option("--required-for-validation"),
        ] = False,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_link_add(
            ctx,
            task_ref or task_arg,
            path=path,
            kind=kind,
            label=label,
            required_for_validation=required_for_validation,
        )

    @app.command("link")
    def link_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "code",
        label: Annotated[str | None, typer.Option("--label")] = None,
        required_for_validation: Annotated[
            bool,
            typer.Option("--required-for-validation"),
        ] = False,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_link_add(
            ctx,
            task_ref or task_arg,
            path=path,
            kind=kind,
            label=label,
            required_for_validation=required_for_validation,
        )

    @app.command("remove")
    def remove_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_link_remove(ctx, task_ref or task_arg, path=path)

    @app.command("unlink")
    def unlink_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_link_remove(ctx, task_ref or task_arg, path=path)

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_link_list(ctx, task_ref or task_arg)


def register_require_v2_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        required_task_ref: Annotated[str, typer.Argument(...)],
        legacy_required_task_ref: Annotated[
            str | None,
            typer.Argument(help="Required task ref."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            target_ref, dependency_ref = _split_legacy_secondary_ref(
                task_ref,
                required_task_ref,
                legacy_required_task_ref,
            )
            task = resolve_cli_task(state.cwd, target_ref)
            task = add_requirement(state.cwd, task.id, dependency_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"added requirement on {task.id}")

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            requirements = load_requirements(state.cwd, task.id).requirements
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        refs = [item.task_id for item in requirements]
        emit_payload(
            ctx,
            [item.to_dict() for item in requirements],
            human="\n".join(["REQUIREMENTS", *refs])
            if refs
            else "REQUIREMENTS\n(empty)",
        )

    @app.command("remove")
    def remove_command(
        ctx: typer.Context,
        required_task_ref: Annotated[str, typer.Argument(...)],
        legacy_required_task_ref: Annotated[
            str | None,
            typer.Argument(help="Required task ref."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            target_ref, dependency_ref = _split_legacy_secondary_ref(
                task_ref,
                required_task_ref,
                legacy_required_task_ref,
            )
            task = resolve_cli_task(state.cwd, target_ref)
            task = remove_requirement(state.cwd, task.id, dependency_ref)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"removed requirement on {task.id}")

    @app.command("waive")
    def waive_command(
        ctx: typer.Context,
        required_task_ref: Annotated[str, typer.Argument(...)],
        legacy_required_task_ref: Annotated[
            str | None,
            typer.Argument(help="Required task ref."),
        ] = None,
        actor: Annotated[str, typer.Option("--actor")] = "user",
        reason: Annotated[str, typer.Option("--reason")] = "",
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            target_ref, dependency_ref = _split_legacy_secondary_ref(
                task_ref,
                required_task_ref,
                legacy_required_task_ref,
            )
            task = resolve_cli_task(state.cwd, target_ref)
            task = waive_requirement(
                state.cwd,
                task.id,
                dependency_ref,
                actor_type=actor,
                reason=reason,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, task.to_dict(), human=f"waived requirement on {task.id}")


def _emit_link_add(
    ctx: typer.Context,
    task_ref: str | None,
    *,
    path: str,
    kind: str,
    label: str | None,
    required_for_validation: bool,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        task = add_file_link(
            state.cwd,
            task.id,
            path=path,
            kind=kind,
            label=label,
            required_for_validation=required_for_validation,
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, task.to_dict(), human=f"linked file on {task.id}")


def _split_legacy_secondary_ref(
    task_ref: str | None,
    primary_ref: str,
    secondary_ref: str | None,
) -> tuple[str | None, str]:
    if secondary_ref is None:
        return task_ref, primary_ref
    return task_ref or primary_ref, secondary_ref


def _emit_link_remove(ctx: typer.Context, task_ref: str | None, *, path: str) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        task = remove_file_link(state.cwd, task.id, path=path)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, task.to_dict(), human=f"unlinked file on {task.id}")


def _emit_link_list(ctx: typer.Context, task_ref: str | None) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        payload = list_file_links(state.cwd, task.id)
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


def register_lock_v2_commands(app: typer.Typer) -> None:
    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            payload = show_lock(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=str(payload["lock"]))

    @app.command("break")
    def break_command(
        ctx: typer.Context,
        reason: Annotated[str, typer.Option("--reason")],
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref or task_arg)
            payload = break_lock(state.cwd, task.id, reason=reason)
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
        format_name: Annotated[str, typer.Option("--format")] = "text",
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_handoff(ctx, task_ref or task_arg, mode="show", format_name=format_name)

    @app.command("plan-context")
    def plan_context_command(
        ctx: typer.Context,
        format_name: Annotated[str, typer.Option("--format")] = "text",
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_handoff(
            ctx,
            task_ref or task_arg,
            mode="plan-context",
            format_name=format_name,
        )

    @app.command("implementation-context")
    def implementation_context_command(
        ctx: typer.Context,
        format_name: Annotated[str, typer.Option("--format")] = "text",
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_handoff(
            ctx,
            task_ref or task_arg,
            mode="implementation-context",
            format_name=format_name,
        )

    @app.command("validation-context")
    def validation_context_command(
        ctx: typer.Context,
        format_name: Annotated[str, typer.Option("--format")] = "text",
        task_arg: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_handoff(
            ctx,
            task_ref or task_arg,
            mode="validation-context",
            format_name=format_name,
        )


def emit_next_action_command(
    ctx: typer.Context,
    task_ref: str | None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        payload = next_action(state.cwd, task.id)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, payload, human=f"{payload['action']}: {payload['reason']}")


def emit_can_command(ctx: typer.Context, task_ref: str | None, action: str) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        payload = can_perform(state.cwd, task.id, action)
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
        human=(
            f"healthy: {payload['healthy']} "
            f"errors: {len(cast(list[object], payload['errors']))}"
        ),
    )


def emit_doctor_locks_command(ctx: typer.Context) -> None:
    state = cli_state_from_context(ctx)
    payload = inspect_v2_locks(state.cwd)
    emit_payload(
        ctx,
        payload,
        human=_expired_locks_human(payload["expired_locks"]),
    )


def emit_doctor_schema_command(ctx: typer.Context) -> None:
    state = cli_state_from_context(ctx)
    payload = inspect_v2_schema(state.cwd)
    emit_payload(
        ctx,
        payload,
        human=f"schema healthy: {payload['healthy']}",
    )


def emit_doctor_indexes_command(ctx: typer.Context) -> None:
    state = cli_state_from_context(ctx)
    payload = inspect_v2_indexes(state.cwd)
    emit_payload(
        ctx,
        payload,
        human=f"indexes healthy: {payload['healthy']}",
    )


def _emit_todo_update(
    ctx: typer.Context,
    task_ref: str | None,
    todo_id: str,
    *,
    done: bool,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        task = set_todo_done(state.cwd, task.id, todo_id, done=done)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, task.to_dict(), human=f"updated todo {todo_id}")


def _emit_handoff(
    ctx: typer.Context,
    task_ref: str | None,
    *,
    mode: str,
    format_name: str,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        payload = render_handoff(
            state.cwd,
            task.id,
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
