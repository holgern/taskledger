from __future__ import annotations

from typing import Annotated

import typer

from taskledger.cli_common import (
    TaskOption,
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    render_json,
    resolve_cli_task,
)
from taskledger.errors import LaunchError
from taskledger.services.handoff import render_handoff
from taskledger.services.worker_pipeline import (
    worker_pipeline_list,
    worker_pipeline_next,
    worker_pipeline_show,
    worker_pipeline_status,
)


def register_pipeline_commands(app: typer.Typer) -> None:
    @app.command("show")
    def show_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = worker_pipeline_show(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=_pipeline_show_human(payload))

    @app.command("list")
    def list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = worker_pipeline_list(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=_pipeline_list_human(payload))

    @app.command("next")
    def next_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            status = worker_pipeline_status(state.cwd)
            if not bool(status["configured"]) or not bool(status["enabled"]):
                payload = {
                    "kind": "worker_pipeline_next",
                    "configured": status["configured"],
                    "enabled": status["enabled"],
                    "task_id": None,
                    "step": None,
                    "reason": status["message"],
                }
            else:
                task = resolve_cli_task(state.cwd, task_ref)
                payload = worker_pipeline_next(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, payload, human=_pipeline_next_human(payload))

    @app.command("context")
    def context_command(
        ctx: typer.Context,
        step_id: Annotated[str, typer.Argument(help="Configured worker step id.")],
        task_ref: TaskOption = None,
        scope: Annotated[
            str | None,
            typer.Option("--scope", help="Context scope: task, todo, or run."),
        ] = None,
        todo_id: Annotated[
            str | None, typer.Option("--todo", help="Focus on one todo id.")
        ] = None,
        focus_run_id: Annotated[
            str | None, typer.Option("--run", help="Focus on one run id.")
        ] = None,
        format_name: Annotated[str, typer.Option("--format")] = "markdown",
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = render_handoff(
                state.cwd,
                task.id,
                worker_step_id=step_id,
                scope=scope,
                todo_id=todo_id,
                focus_run_id=focus_run_id,
                format_name=format_name,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        human = (
            payload
            if isinstance(payload, str)
            else render_json(payload)
            if format_name == "json"
            else None
        )
        emit_payload(ctx, payload, human=human)


def _pipeline_show_human(payload: dict[str, object]) -> str:
    if not bool(payload.get("configured")) or not bool(payload.get("enabled")):
        return str(payload.get("message") or "No worker pipeline configured.")
    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return "Worker pipeline is enabled."
    lines = [
        f"Worker pipeline: {pipeline.get('name')}",
        f"mode: {pipeline.get('mode')}",
        "steps:",
    ]
    steps = pipeline.get("steps")
    if isinstance(steps, list) and steps:
        for item in steps:
            if isinstance(item, dict):
                lines.append(
                    "- "
                    f"{item.get('id')}  {item.get('label')}  "
                    f"{item.get('lifecycle_stage')}  {item.get('base_context')}"
                )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _pipeline_list_human(payload: dict[str, object]) -> str:
    if not bool(payload.get("configured")) or not bool(payload.get("enabled")):
        return str(payload.get("message") or "No worker pipeline configured.")
    steps = payload.get("steps")
    lines = ["WORKER PIPELINE STEPS"]
    if isinstance(steps, list) and steps:
        for item in steps:
            if isinstance(item, dict):
                lines.append(
                    f"{item.get('id')}  {item.get('label')}  "
                    f"{item.get('lifecycle_stage')}"
                )
    else:
        lines.append("(empty)")
    return "\n".join(lines)


def _pipeline_next_human(payload: dict[str, object]) -> str:
    step = payload.get("step")
    reason = str(payload.get("reason") or "")
    if not isinstance(step, dict):
        return reason or "No worker pipeline step is pending."
    lines = [f"Next worker step: {step.get('id')}"]
    label = step.get("label")
    if isinstance(label, str) and label.strip():
        lines.append(f"Label: {label}")
    lines.append(reason)
    return "\n".join(lines)
