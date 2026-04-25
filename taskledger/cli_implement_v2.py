from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.task_runs import (
    add_change,
    add_implementation_artifact,
    add_implementation_deviation,
    finish_implementation,
    log_implementation,
    run_implementation_command,
    scan_changes,
    show_task_run,
    start_implementation,
)
from taskledger.api.tasks import todo_status
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    render_json,
    resolve_cli_task,
)
from taskledger.errors import LaunchError
from taskledger.services.actors import resolve_actor, resolve_harness
from taskledger.storage.v2 import load_todos


def register_implement_v2_commands(app: typer.Typer) -> None:  # noqa: C901
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        actor: Annotated[
            str | None,
            typer.Option("--actor", help="Actor type: user, agent, or system."),
        ] = None,
        actor_name: Annotated[
            str | None,
            typer.Option("--actor-name", help="Actor name."),
        ] = None,
        actor_role: Annotated[
            str | None,
            typer.Option("--actor-role", help="Actor role in task lifecycle."),
        ] = None,
        harness: Annotated[
            str | None,
            typer.Option("--harness", help="Harness name."),
        ] = None,
        session_id: Annotated[
            str | None,
            typer.Option("--session-id", help="Session identifier."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            resolved_actor = resolve_actor(
                actor_type=actor,
                actor_name=actor_name,
                role=actor_role,
                session_id=session_id,
            )
            resolved_harness = resolve_harness(name=harness, session_id=session_id)
            payload = start_implementation(
                state.cwd,
                task.id,
                actor=resolved_actor,
                harness=resolved_harness,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"started implementation {payload['run_id']}",
        )

    @app.command("log")
    def log_command(
        ctx: typer.Context,
        message: Annotated[str | None, typer.Option("--message")] = None,
        json_output: Annotated[
            bool,
            typer.Option("--json", help="Render machine-readable JSON."),
        ] = False,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            if message is None:
                payload = show_task_run(
                    state.cwd,
                    task.id,
                    run_id=None,
                    run_type="implementation",
                )
                if json_output and not state.json_output:
                    typer.echo(render_json(payload))
                    return
                emit_payload(ctx, payload, human=str(payload["run"]))
                return
            run = log_implementation(state.cwd, task.id, message=message)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged implementation {run.run_id}")

    def _emit_change_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
        command: Annotated[str | None, typer.Option("--command")] = None,
        git_diff_stat: Annotated[str | None, typer.Option("--git-diff-stat")] = None,
        task_ref: str | None = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            change = add_change(
                state.cwd,
                task.id,
                path=path,
                kind=kind,
                summary=summary,
                command=command,
                git_diff_stat=git_diff_stat,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, change.to_dict(), human=f"logged change {change.change_id}")

    @app.command("change")
    def change_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
        command: Annotated[str | None, typer.Option("--command")] = None,
        git_diff_stat: Annotated[str | None, typer.Option("--git-diff-stat")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_change_command(ctx, path, kind, summary, command, git_diff_stat, task_ref)

    @app.command("add-change")
    def add_change_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        kind: Annotated[str, typer.Option("--kind")] = "edit",
        summary: Annotated[str, typer.Option("--summary")] = "",
        command: Annotated[str | None, typer.Option("--command")] = None,
        git_diff_stat: Annotated[str | None, typer.Option("--git-diff-stat")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_change_command(ctx, path, kind, summary, command, git_diff_stat, task_ref)

    @app.command("scan-changes")
    def scan_changes_command(
        ctx: typer.Context,
        from_git: Annotated[bool, typer.Option("--from-git")] = False,
        summary: Annotated[str, typer.Option("--summary")] = "",
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            change = scan_changes(
                state.cwd,
                task.id,
                from_git=from_git,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, change.to_dict(), human=f"logged change {change.change_id}")

    @app.command(
        "command",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def command_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        argv = tuple(ctx.args)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = run_implementation_command(
                state.cwd,
                task.id,
                argv=argv,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"ran implementation command exit={payload['exit_code']}",
        )

    @app.command("deviation")
    def deviation_command(
        ctx: typer.Context,
        message: Annotated[str, typer.Option("--message")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = add_implementation_deviation(state.cwd, task.id, message=message)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged deviation on {run.run_id}")

    @app.command("artifact")
    def artifact_command(
        ctx: typer.Context,
        path: Annotated[str, typer.Option("--path")],
        summary: Annotated[str, typer.Option("--summary")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = add_implementation_artifact(
                state.cwd,
                task.id,
                path=path,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"logged artifact on {run.run_id}")

    @app.command("finish")
    def finish_command(
        ctx: typer.Context,
        summary: Annotated[str, typer.Option("--summary")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = finish_implementation(state.cwd, task.id, summary=summary)
        except LaunchError as exc:
            if state.json_output:
                emit_error(ctx, exc)
            else:
                from taskledger.cli_common import _error_envelope

                typer.echo(
                    render_json(
                        _error_envelope(
                            ctx,
                            exc,
                            data=None,
                            remediation=None,
                            exit_code=None,
                            error_type=None,
                        )
                    )
                )
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        if state.json_output:
            emit_payload(
                ctx,
                payload,
                human=f"finished implementation {payload['run_id']}",
            )
        else:
            typer.echo(render_json(payload))

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        run_id: Annotated[str | None, typer.Option("--run")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = show_task_run(
                state.cwd,
                task.id,
                run_id=run_id,
                run_type="implementation",
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        run = payload["run"]
        assert isinstance(run, dict)
        emit_payload(ctx, payload, human=f"{run['run_id']}  {run['status']}")

    @app.command("status")
    def status_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = todo_status(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        
        # Build human-readable output
        total = payload.get("total", 0)
        done = payload.get("done", 0)
        can_finish = payload.get("can_finish_implementation", False)
        lines = [f"IMPLEMENTATION STATUS {payload['task_id']}  {done}/{total} todos done"]
        
        todos = load_todos(state.cwd, task.id).todos
        for todo in todos:
            status_mark = "[x]" if todo.done else "[ ]"
            lines.append(f"{status_mark} {todo.id}  {todo.text}")
        
        if can_finish:
            lines.append(f"\nReady: All todos done. Run 'taskledger implement finish --summary \"...\"'")
        else:
            lines.append(f"\nBlocked: {total - done} todos not done.")
        
        emit_payload(ctx, payload, human="\n".join(lines))

    @app.command("checklist")
    def checklist_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = todo_status(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        
        # Build human-readable checklist output
        total = payload.get("total", 0)
        done = payload.get("done", 0)
        can_finish = payload.get("can_finish_implementation", False)
        lines = [f"TODO CHECKLIST: {done}/{total} done"]
        
        todos = load_todos(state.cwd, task.id).todos
        for todo in todos:
            status_mark = "[x]" if todo.done else "[ ]"
            lines.append(f"{status_mark} {todo.id}  {todo.text}")
        
        if can_finish:
            lines.append(f"\n✓ All todos done!")
        else:
            lines.append(f"\n{total - done} todos remaining")
        
        emit_payload(ctx, payload, human="\n".join(lines))
