from __future__ import annotations

from typing import Annotated, Any, cast

import typer

from taskledger.api.task_runs import (
    add_validation_check,
    finish_validation,
    show_task_run,
    start_validation,
    validation_status,
    waive_criterion,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    resolve_cli_task,
)
from taskledger.errors import LaunchError
from taskledger.services.actors import resolve_actor, resolve_harness


def _render_validation_status(payload: dict[str, Any]) -> str:
    """Render validation gate report to human-readable text."""
    lines = []

    task_id = payload.get("task_id", "?")
    task_slug = payload.get("task_slug", "?")
    lines.append(f"Validation status for {task_slug} ({task_id})")
    lines.append("")

    run_id = payload.get("run_id", "?")
    lines.append(f"Run: {run_id}")
    lines.append("")

    accepted_plan = payload.get("accepted_plan", {})
    plan_version = accepted_plan.get("version", "none")
    plan_status = accepted_plan.get("status", "none")
    lines.append(f"Accepted plan: v{plan_version} {plan_status}")

    implementation = payload.get("implementation", {})
    impl_run_id = implementation.get("run_id", "none")
    impl_status = implementation.get("status", "none")
    lines.append(f"Implementation: {impl_run_id} {impl_status}")
    lines.append("")

    lines.append("Criteria:")
    criteria = payload.get("criteria", [])
    for crit in criteria:
        crit_id = crit.get("id", "?")
        mandatory = "[mandatory]" if crit.get("mandatory") else ""
        latest_status = crit.get("latest_status", "not_run")
        satisfied = crit.get("satisfied", False)
        checkbox = "[x]" if satisfied else "[ ]"
        text = crit.get("text", "")
        lines.append(f"  {checkbox} {crit_id} {mandatory} {latest_status}")
        if text:
            lines.append(f"      {text}")
        evidence = crit.get("evidence", [])
        if evidence:
            lines.append(f"      evidence: {', '.join(evidence)}")
    lines.append("")

    todos = payload.get("todos", {})
    open_todos = todos.get("open_mandatory", [])
    if open_todos:
        lines.append("Mandatory todos:")
        for todo_id in open_todos:
            lines.append(f"  [ ] {todo_id}")
        lines.append("")

    dependencies = payload.get("dependencies", {})
    dep_blockers = dependencies.get("blockers", [])
    if dep_blockers:
        lines.append("Dependencies:")
        for blocker in dep_blockers:
            lines.append(f"  - {blocker}")
        lines.append("")

    can_finish = payload.get("can_finish_passed", False)
    lines.append(f"Can finish passed: {'yes' if can_finish else 'no'}")

    blockers = payload.get("blockers", [])
    if blockers:
        lines.append("")
        lines.append("Blockers:")
        for blocker in blockers:
            kind = blocker.get("kind", "?")
            ref = blocker.get("ref", "")
            message = blocker.get("message", "")
            hint = blocker.get("command_hint", "")
            ref_str = f" {ref}" if ref else ""
            lines.append(f"  - {kind}{ref_str}: {message}")
            if hint:
                lines.append(f"    {hint}")

    return "\n".join(lines)


def register_validate_v2_commands(app: typer.Typer) -> None:
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
            payload = start_validation(
                state.cwd,
                task.id,
                actor=resolved_actor,
                harness=resolved_harness,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"started validation {payload['run_id']}")

    def _emit_check(
        ctx: typer.Context,
        *,
        name: str | None,
        criterion: str | None,
        status: str,
        details: str | None,
        evidence: list[str] | None,
        task_ref: str | None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            run = add_validation_check(
                state.cwd,
                task.id,
                name=name,
                criterion_id=criterion,
                status=status,
                details=details,
                evidence=tuple(evidence or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"added check to {run.run_id}")

    @app.command("check")
    def check_command(
        ctx: typer.Context,
        criterion: Annotated[str, typer.Option("--criterion")],
        status: Annotated[str, typer.Option("--status")] = "pass",
        evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
        name: Annotated[str | None, typer.Option("--name")] = None,
        details: Annotated[str | None, typer.Option("--details")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_check(
            ctx,
            name=name,
            criterion=criterion,
            status=status,
            details=details,
            evidence=evidence,
            task_ref=task_ref,
        )

    @app.command("add-check")
    def add_check_command(
        ctx: typer.Context,
        name: Annotated[str | None, typer.Option("--name")] = None,
        criterion: Annotated[str | None, typer.Option("--criterion")] = None,
        status: Annotated[str, typer.Option("--status")] = "pass",
        details: Annotated[str | None, typer.Option("--details")] = None,
        evidence: Annotated[list[str] | None, typer.Option("--evidence")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        _emit_check(
            ctx,
            name=name,
            criterion=criterion,
            status=status,
            details=details,
            evidence=evidence,
            task_ref=task_ref,
        )

    @app.command("finish")
    def finish_command(
        ctx: typer.Context,
        result: Annotated[str, typer.Option("--result")],
        summary: Annotated[str, typer.Option("--summary")],
        recommendation: Annotated[str | None, typer.Option("--recommendation")] = None,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = finish_validation(
                state.cwd,
                task.id,
                result=result,
                summary=summary,
                recommendation=recommendation,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=f"finished validation {payload['run_id']}")

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
                run_type="validation",
            )
            status_payload = validation_status(state.cwd, task.id, run_id=run_id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        run = payload["run"]
        assert isinstance(run, dict)
        status_result = cast(dict[str, Any], status_payload.get("result", {}))
        human_output = _render_validation_status(status_result)
        emit_payload(ctx, payload, human=human_output)

    @app.command("status")
    def status_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
        run: Annotated[str | None, typer.Option("--run")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = validation_status(state.cwd, task.id, run_id=run)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        result = cast(dict[str, Any], payload.get("result", {}))
        human_output = _render_validation_status(result)
        emit_payload(ctx, payload, human=human_output)

    @app.command("waive")
    def waive_command(
        ctx: typer.Context,
        criterion: Annotated[str, typer.Option("--criterion")],
        reason: Annotated[str, typer.Option("--reason")],
        actor: Annotated[str, typer.Option("--actor")] = "user",
        task_ref: Annotated[
            str | None,
            typer.Argument(help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            if actor != "user":
                raise LaunchError("Only user actors can waive criteria.")
            task = resolve_cli_task(state.cwd, task_ref)
            run = waive_criterion(
                state.cwd,
                task.id,
                criterion_id=criterion,
                reason=reason,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, run.to_dict(), human=f"waived criterion {criterion}")
