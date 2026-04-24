from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.questions import (
    add_question,
    answer_question,
    dismiss_question,
    list_open_questions,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    resolve_cli_task,
)
from taskledger.errors import LaunchError
from taskledger.storage.v2 import list_questions


def register_question_v2_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        text: Annotated[str, typer.Option("--text")],
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            question = add_question(state.cwd, task.id, text=text)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, question.to_dict(), human=f"added question {question.id}")

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
            payload = [item.to_dict() for item in list_questions(state.cwd, task.id)]
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        lines = ["QUESTIONS"]
        for item in payload:
            lines.append(f"{item['id']}  {item['status']}  {item['question']}")
        emit_payload(
            ctx,
            payload,
            human="\n".join(lines) if payload else "QUESTIONS\n(empty)",
        )

    @app.command("answer")
    def answer_command(
        ctx: typer.Context,
        question_id: Annotated[str, typer.Argument(..., help="Question id.")],
        text: Annotated[str, typer.Option("--text")],
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            question = answer_question(state.cwd, task.id, question_id, text=text)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, question.to_dict(), human=f"answered {question.id}")

    @app.command("dismiss")
    def dismiss_command(
        ctx: typer.Context,
        question_id: Annotated[str, typer.Argument(..., help="Question id.")],
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            question = dismiss_question(state.cwd, task.id, question_id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(ctx, question.to_dict(), human=f"dismissed {question.id}")

    @app.command("open")
    def open_command(
        ctx: typer.Context,
        task_ref: Annotated[
            str | None,
            typer.Option("--task", help="Task ref. Defaults to the active task."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            payload = list_open_questions(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        questions = payload["questions"]
        assert isinstance(questions, list)
        lines = ["OPEN QUESTIONS"]
        for item in questions:
            if isinstance(item, dict):
                lines.append(f"{item['id']}  {item['question']}")
        emit_payload(
            ctx,
            payload,
            human="\n".join(lines) if questions else "OPEN QUESTIONS\n(empty)",
        )
