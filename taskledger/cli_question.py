from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Literal, cast

import typer
import yaml

from taskledger.api.questions import (
    add_question,
    add_questions,
    answer_question,
    answer_questions,
    dismiss_question,
    list_open_questions,
    question_status,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    launch_error_exit_code,
    read_text_input,
    resolve_cli_task,
)
from taskledger.domain.models import ActorRef
from taskledger.errors import LaunchError
from taskledger.storage.task_store import list_questions

_QUESTION_ANSWER_RE = re.compile(r"^(q-\d+):\s*(.+)$")


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping_unique_keys(
    loader: yaml.Loader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise LaunchError(f"Duplicate key in answers input: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_unique_keys,
)


def _parse_answer_many_input(raw: str) -> dict[str, str]:
    try:
        parsed = yaml.load(raw, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise LaunchError(f"Invalid answers YAML: {exc}") from exc
    if isinstance(parsed, dict):
        raw_answers = parsed.get("answers", parsed)
        if not isinstance(raw_answers, dict):
            raise LaunchError("answers must be a mapping of question ids to text.")
        answers: dict[str, str] = {}
        for key, value in raw_answers.items():
            question_id = str(key).strip()
            if not re.fullmatch(r"q-\d+", question_id):
                raise LaunchError(f"Invalid question id in answers input: {key}")
            if not isinstance(value, str):
                raise LaunchError(f"Answer for {question_id} must be text.")
            answers[question_id] = value
        return answers
    answers = {}
    for line_number, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        match = _QUESTION_ANSWER_RE.match(stripped)
        if match is None:
            raise LaunchError(
                "Plain answer input must use 'q-0001: answer' lines; "
                f"line {line_number} was invalid."
            )
        question_id, answer = match.groups()
        if question_id in answers:
            raise LaunchError(f"Duplicate question id in answers input: {question_id}")
        answers[question_id] = answer
    if not answers:
        raise LaunchError("At least one answer is required.")
    return answers


def _add_command(
    ctx: typer.Context,
    text: Annotated[str, typer.Option("--text")],
    required_for_plan: Annotated[
        bool,
        typer.Option("--required-for-plan"),
    ] = False,
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        question = add_question(
            state.cwd,
            task.id,
            text=text,
            required_for_plan=required_for_plan,
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, question.to_dict(), human=f"added question {question.id}")


def _parse_question_add_many_text(
    raw: str,
    *,
    required_for_plan: bool,
) -> list[tuple[str, bool]]:
    questions: list[tuple[str, bool]] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            raise LaunchError(
                "Question batch text must not contain empty or whitespace-only "
                f"lines; line {line_number} was empty."
            )
        questions.append((stripped, required_for_plan))
    if not questions:
        raise LaunchError("At least one question is required.")
    return questions


def _parse_question_add_many_yaml(
    raw: str,
    *,
    required_for_plan: bool,
) -> list[tuple[str, bool]]:
    try:
        parsed = yaml.load(raw, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise LaunchError(f"Invalid questions YAML: {exc}") from exc
    raw_questions = (
        parsed.get("questions", parsed) if isinstance(parsed, dict) else parsed
    )
    if not isinstance(raw_questions, list):
        raise LaunchError(
            "questions input must be a list or a mapping with `questions`."
        )
    questions: list[tuple[str, bool]] = []
    for index, item in enumerate(raw_questions, start=1):
        if isinstance(item, str):
            questions.append((item, required_for_plan))
            continue
        if not isinstance(item, dict):
            raise LaunchError(f"Question item {index} must be text or a mapping.")
        text = item.get("text")
        if not isinstance(text, str):
            raise LaunchError(f"Question item {index} must define text.")
        raw_required = item.get("required_for_plan", required_for_plan)
        if not isinstance(raw_required, bool):
            raise LaunchError(
                f"Question item {index} has non-boolean required_for_plan."
            )
        questions.append((text, raw_required))
    if not questions:
        raise LaunchError("At least one question is required.")
    return questions


def _add_many_command(
    ctx: typer.Context,
    text: Annotated[str | None, typer.Option("--text")] = None,
    yaml_file: Annotated[Path | None, typer.Option("--yaml-file")] = None,
    required_for_plan: Annotated[
        bool,
        typer.Option("--required-for-plan"),
    ] = False,
    allow_duplicates: Annotated[
        bool,
        typer.Option("--allow-duplicates"),
    ] = False,
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        if (text is None) == (yaml_file is None):
            raise LaunchError("Provide exactly one of --text or --yaml-file.")
        task = resolve_cli_task(state.cwd, task_ref)
        if text is not None:
            questions = _parse_question_add_many_text(
                text,
                required_for_plan=required_for_plan,
            )
        else:
            assert yaml_file is not None
            raw = read_text_input(
                text=None,
                from_file=yaml_file,
                text_label="--yaml-file",
            )
            questions = _parse_question_add_many_yaml(
                raw,
                required_for_plan=required_for_plan,
            )
        payload = add_questions(
            state.cwd,
            task.id,
            questions,
            allow_duplicates=allow_duplicates,
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    added_ids = cast(list[str], payload["added_question_ids"])
    emit_payload(
        ctx,
        payload,
        human=f"added {len(added_ids)} questions: {', '.join(added_ids)}",
    )


def _list_command(
    ctx: typer.Context,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Comma-separated status filter, e.g. answered,dismissed.",
        ),
    ] = None,
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        all_questions = list_questions(state.cwd, task.id)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    status_filter: set[str] | None = None
    if status is not None:
        status_filter = {s.strip() for s in status.split(",") if s.strip()}
    filtered = (
        [q for q in all_questions if q.status in status_filter]
        if status_filter is not None
        else all_questions
    )
    payload = [item.to_dict() for item in filtered]
    lines = ["QUESTIONS"]
    for item in payload:
        lines.append(f"{item['id']}  {item['status']}  {item['question']}")
    emit_payload(
        ctx,
        payload,
        human="\n".join(lines) if payload else "QUESTIONS\n(empty)",
    )


def _answer_command(
    ctx: typer.Context,
    question_id: Annotated[str, typer.Argument(..., help="Question id.")],
    text: Annotated[str, typer.Option("--text")],
    actor: Annotated[str, typer.Option("--actor")] = "user",
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        question = answer_question(
            state.cwd,
            task.id,
            question_id,
            text=text,
            actor=ActorRef(
                actor_type=cast(Literal["agent", "user", "system"], actor),
                actor_name=actor,
            ),
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(ctx, question.to_dict(), human=f"answered {question.id}")


def _answer_many_command(
    ctx: typer.Context,
    text: Annotated[str | None, typer.Option("--text")] = None,
    from_file: Annotated[Path | None, typer.Option("--file")] = None,
    actor: Annotated[str, typer.Option("--actor")] = "user",
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        raw = read_text_input(text=text, from_file=from_file)
        payload = answer_questions(
            state.cwd,
            task.id,
            _parse_answer_many_input(raw),
            actor=ActorRef(
                actor_type=cast(Literal["agent", "user", "system"], actor),
                actor_name=actor,
            ),
            answer_source="harness",
        )
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(
        ctx,
        payload,
        human=(
            f"answered {len(cast(list[object], payload['answered_question_ids']))} "
            "questions\n" + _render_question_status_human(payload)
        ),
    )


def _dismiss_command(
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


def _open_command(
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


def _answers_command(
    ctx: typer.Context,
    format_name: Annotated[
        str,
        typer.Option("--format", help="Output format: markdown or json."),
    ] = "markdown",
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        all_questions = list_questions(state.cwd, task.id)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    answered = [q for q in all_questions if q.status == "answered"]
    payload_dicts = [q.to_dict() for q in answered]
    payload = {
        "kind": "question_answers",
        "task_id": task.id,
        "questions": payload_dicts,
    }
    if format_name == "json":
        emit_payload(ctx, payload)
        return
    lines = ["ANSWERED QUESTIONS"]
    for q in answered:
        lines.append("")
        lines.append(f"### {q.id}")
        lines.append(f"Q: {q.question}")
        lines.append(f"A: {q.answer}")
    emit_payload(
        ctx,
        payload,
        human="\n".join(lines) if answered else "ANSWERED QUESTIONS\n(empty)",
    )


def _status_command(
    ctx: typer.Context,
    task_ref: Annotated[
        str | None,
        typer.Option("--task", help="Task ref. Defaults to the active task."),
    ] = None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        task = resolve_cli_task(state.cwd, task_ref)
        payload = question_status(state.cwd, task.id)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    emit_payload(
        ctx,
        payload,
        human=_render_question_status_human(payload),
    )


def _render_question_status_human(payload: dict[str, object]) -> str:
    lines = [
        f"Required open: {payload['required_open']}",
        f"Plan regeneration needed: {payload['plan_regeneration_needed']}",
        f"Next: {payload['next_action']}",
    ]
    template_command = payload.get("template_command")
    if isinstance(template_command, str):
        lines.append(f"Template: {template_command}")
    required_fields = payload.get("required_plan_fields")
    if isinstance(required_fields, list) and required_fields:
        lines.append(
            "Required front matter: " + ", ".join(str(item) for item in required_fields)
        )
    recommended_fields = payload.get("recommended_plan_fields")
    if isinstance(recommended_fields, list) and recommended_fields:
        lines.append(
            "Recommended front matter: "
            + ", ".join(str(item) for item in recommended_fields)
        )
    return "\n".join(lines)


def register_question_v2_commands(app: typer.Typer) -> None:
    app.command("add")(_add_command)
    app.command("add-many")(_add_many_command)
    app.command("list")(_list_command)
    app.command("answer")(_answer_command)
    app.command("answer-many")(_answer_many_command)
    app.command("dismiss")(_dismiss_command)
    app.command("open")(_open_command)
    app.command("answers")(_answers_command)
    app.command("status")(_status_command)
