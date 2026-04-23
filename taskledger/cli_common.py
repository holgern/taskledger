from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from taskledger.errors import LaunchError


@dataclass(slots=True, frozen=True)
class CLIState:
    cwd: Path
    json_output: bool


def resolve_workspace_root(cwd: Path | None) -> Path:
    return (cwd or Path.cwd()).expanduser().resolve()


def cli_state_from_context(ctx: typer.Context) -> CLIState:
    state = ctx.obj
    if not isinstance(state, CLIState):
        raise LaunchError("Taskledger CLI state is not initialized.")
    return state


def render_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def emit_payload(ctx: typer.Context, payload: Any, *, human: str | None = None) -> None:
    state = cli_state_from_context(ctx)
    if state.json_output:
        typer.echo(render_json(payload))
        return
    if human is None:
        if isinstance(payload, dict):
            human = "\n".join(
                f"{key}: {value}" for key, value in payload.items() if value is not None
            )
        else:
            human = str(payload)
    typer.echo(human)


def emit_error(ctx: typer.Context, message: str) -> None:
    state = cli_state_from_context(ctx)
    if state.json_output:
        typer.echo(render_json({"error": message}))
    else:
        typer.echo(message, err=True)


def read_text_input(
    *, text: str | None, from_file: Path | None, text_label: str = "--text"
) -> str:
    if text and from_file is not None:
        raise LaunchError(f"Use either {text_label} or --from-file, not both.")
    if from_file is not None:
        try:
            return from_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise LaunchError(f"Failed to read {from_file}: {exc}") from exc
    if text is None:
        raise LaunchError(f"Provide {text_label} or --from-file.")
    if not text.strip():
        raise LaunchError("Text input must not be empty.")
    return text


def write_text_output(path: Path, text: str) -> Path:
    target = path.expanduser()
    parent = target.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise LaunchError(f"Failed to write {target}: {exc}") from exc
    return target


def human_kv(title: str, rows: list[tuple[str, object]]) -> str:
    lines = [title]
    for key, value in rows:
        if value is None:
            continue
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def human_list(title: str, rows: list[str]) -> str:
    if not rows:
        return f"{title}\n(empty)"
    return "\n".join([title, *rows])
