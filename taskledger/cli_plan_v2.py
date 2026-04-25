from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.plans import (
    approve_plan,
    diff_plan,
    list_plan_versions,
    materialize_plan_todos,
    propose_plan,
    regenerate_plan_from_answers,
    reject_plan,
    revise_plan,
    show_plan,
    start_planning,
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
from taskledger.services.actors import resolve_actor, resolve_harness


def register_plan_v2_commands(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
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
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            resolved_actor = resolve_actor(
                actor_type=actor,
                actor_name=actor_name,
                role=actor_role,
                session_id=session_id,
            )
            resolved_harness = resolve_harness(name=harness, session_id=session_id)
            payload = start_planning(
                state.cwd,
                task.id,
                actor=resolved_actor,
                harness=resolved_harness,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"started planning {payload['task_id']}")

    @app.command("propose")
    def propose_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        text: Annotated[str | None, typer.Option("--text")] = None,
        from_file: Annotated[Path | None, typer.Option("--file")] = None,
        criterion: Annotated[list[str] | None, typer.Option("--criterion")] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = propose_plan(
                state.cwd,
                task.id,
                body=read_text_input(text=text, from_file=from_file),
                criteria=tuple(criterion or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"proposed plan v{payload['plan_version']} for {payload['task_id']}",
        )

    @app.command("draft")
    def draft_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        ask_questions: Annotated[bool, typer.Option("--ask-questions")] = False,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = {
                "kind": "plan_draft_context",
                "task_id": task.id,
                "ask_questions": ask_questions,
                "next_action": (
                    "taskledger question add --text \"...\" --required-for-plan"
                    if ask_questions
                    else "taskledger plan propose --file plan.md"
                ),
            }
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=str(payload["next_action"]))

    @app.command("regenerate")
    def regenerate_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        from_answers: Annotated[bool, typer.Option("--from-answers")] = False,
        text: Annotated[str | None, typer.Option("--text")] = None,
        from_file: Annotated[Path | None, typer.Option("--file")] = None,
        allow_open_questions: Annotated[
            bool,
            typer.Option("--allow-open-questions"),
        ] = False,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            if not from_answers:
                raise LaunchError("plan regenerate requires --from-answers.")
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = regenerate_plan_from_answers(
                state.cwd,
                task.id,
                body=read_text_input(text=text, from_file=from_file),
                allow_open_questions=allow_open_questions,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"regenerated plan v{payload['plan_version']} for {payload['task_id']}",
        )

    @app.command("materialize-todos")
    def materialize_todos_command(
        ctx: typer.Context,
        version: Annotated[int, typer.Option("--version")],
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = materialize_plan_todos(
                state.cwd,
                task.id,
                version=version,
                dry_run=dry_run,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"materialized {payload['materialized_todos']} todos",
        )

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        version: Annotated[int | None, typer.Option("--version")] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = show_plan(state.cwd, task.id, version=version)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        plan = payload["plan"]
        assert isinstance(plan, dict)
        emit_payload(
            ctx,
            payload,
            human=f"plan v{plan['plan_version']} ({plan['status']})",
        )

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = list_plan_versions(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        plans = payload["plans"]
        assert isinstance(plans, list)
        lines = ["PLANS"]
        for item in plans:
            if isinstance(item, dict):
                lines.append(f"v{item['plan_version']}  {item['status']}")
        emit_payload(
            ctx, payload, human="\n".join(lines) if plans else "PLANS\n(empty)"
        )

    @app.command("diff")
    def diff_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        from_version: Annotated[int, typer.Option("--from")] = 1,
        to_version: Annotated[int, typer.Option("--to")] = 1,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = diff_plan(
                state.cwd,
                task.id,
                from_version=from_version,
                to_version=to_version,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=str(payload["diff"]))

    @app.command("approve")
    def approve_command(
        ctx: typer.Context,
        version: Annotated[int, typer.Option("--version")],
        actor: Annotated[str, typer.Option("--actor")] = "user",
        actor_name: Annotated[str | None, typer.Option("--actor-name")] = None,
        note: Annotated[str | None, typer.Option("--note")] = None,
        allow_agent_approval: Annotated[
            bool, typer.Option("--allow-agent-approval")
        ] = False,
        reason: Annotated[str | None, typer.Option("--reason")] = None,
        allow_empty_criteria: Annotated[
            bool, typer.Option("--allow-empty-criteria")
        ] = False,
        no_materialize_todos: Annotated[
            bool, typer.Option("--no-materialize-todos")
        ] = False,
        allow_open_questions: Annotated[
            bool, typer.Option("--allow-open-questions")
        ] = False,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = approve_plan(
                state.cwd,
                task.id,
                version=version,
                actor_type=actor,
                actor_name=actor_name,
                note=note,
                allow_agent_approval=allow_agent_approval,
                reason=reason,
                allow_empty_criteria=allow_empty_criteria,
                materialize_todos=not no_materialize_todos,
                allow_open_questions=allow_open_questions,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=f"approved plan v{payload['plan_version']} for {payload['task_id']}",
        )

    @app.command("reject")
    def reject_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        reason: Annotated[str | None, typer.Option("--reason")] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = reject_plan(state.cwd, task.id, reason=reason)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"rejected plan for {payload['task_id']}")

    @app.command("revise")
    def revise_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        task_option: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_option or task_ref)
            payload = revise_plan(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"restarted planning {payload['task_id']}")
