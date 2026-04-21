from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.execution_requests import (
    build_execution_request,
    expand_execution_request,
    record_execution_outcome,
)
from taskledger.cli_common import cli_state_from_context, emit_error, emit_payload
from taskledger.errors import LaunchError
from taskledger.models import ExecutionRequest


@dataclass(slots=True, frozen=True)
class _OutcomeSummary:
    ok: bool
    best_text: str | None


def register_execution_request_commands(app: typer.Typer) -> None:
    @app.command("build")
    def execution_request_build_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
        prompt: Annotated[
            str | None,
            typer.Option("--prompt", help="Optional prompt seed override."),
        ] = None,
        repo_refs: Annotated[
            list[str] | None,
            typer.Option("--repo", help="Repo refs to include. Repeatable."),
        ] = None,
        memory_refs: Annotated[
            list[str] | None,
            typer.Option("--memory", help="Memory refs to include. Repeatable."),
        ] = None,
        file_refs: Annotated[
            list[str] | None,
            typer.Option("--file", help="File refs to include. Repeatable."),
        ] = None,
        item_refs: Annotated[
            list[str] | None,
            typer.Option("--item", help="Item refs to include. Repeatable."),
        ] = None,
        inline_texts: Annotated[
            list[str] | None,
            typer.Option("--inline", help="Inline context snippets. Repeatable."),
        ] = None,
        loop_latest_refs: Annotated[
            list[str] | None,
            typer.Option("--loop-latest", help="Loop latest refs. Repeatable."),
        ] = None,
        run_in_repo: Annotated[
            str | None,
            typer.Option("--run-in-repo", help="Execution repo override."),
        ] = None,
        save_target: Annotated[
            str | None,
            typer.Option("--save-target", help="Save target override."),
        ] = None,
        save_mode: Annotated[
            str | None,
            typer.Option("--save-mode", help="Save mode override."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            request = build_execution_request(
                state.cwd,
                item_ref=item_ref,
                stage_id=stage_id,
                prompt=prompt,
                repo_refs=tuple(repo_refs or ()),
                memory_refs=tuple(memory_refs or ()),
                file_refs=tuple(file_refs or ()),
                item_refs=tuple(item_refs or ()),
                inline_texts=tuple(inline_texts or ()),
                loop_latest_refs=tuple(loop_latest_refs or ()),
                run_in_repo=run_in_repo,
                save_target=save_target,
                save_mode=save_mode,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            request.to_dict(),
            human=(
                f"built execution request {request.request_id} "
                f"for {item_ref}:{stage_id}"
            ),
        )

    @app.command("expand")
    def execution_request_expand_command(
        ctx: typer.Context,
        request_file: Annotated[
            Path,
            typer.Option("--request-file", help="Execution request JSON file."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            request = _execution_request_from_file(request_file)
            expanded = expand_execution_request(state.cwd, request=request)
        except (LaunchError, ValueError) as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            expanded.to_dict(),
            human=(
                f"expanded execution request {expanded.request.request_id} "
                f"({len(expanded.sources)} sources)"
            ),
        )

    @app.command("record-outcome")
    def execution_request_record_outcome_command(
        ctx: typer.Context,
        request_file: Annotated[
            Path,
            typer.Option("--request-file", help="Execution request JSON file."),
        ],
        ok: Annotated[
            bool,
            typer.Option("--ok/--failed", help="Outcome result."),
        ] = True,
        text: Annotated[
            str | None,
            typer.Option("--text", help="Summary text used for the recorded outcome."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            request = _execution_request_from_file(request_file)
            result = record_execution_outcome(
                state.cwd,
                request=request,
                outcome=_OutcomeSummary(ok=ok, best_text=text),
            )
        except (LaunchError, ValueError) as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        payload = result.to_dict() if hasattr(result, "to_dict") else result
        emit_payload(
            ctx,
            payload,
            human=(
                f"recorded {'success' if ok else 'failure'} outcome for "
                f"{request.item_ref}:{request.stage_id}"
            ),
        )


def _execution_request_from_file(path: Path) -> ExecutionRequest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LaunchError(
            f"Failed to read execution request file {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise LaunchError(
            f"Invalid JSON in execution request file {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise LaunchError("Execution request payload must be a JSON object.")
    try:
        return ExecutionRequest.from_dict(payload)
    except ValueError as exc:
        raise LaunchError(f"Invalid execution request payload: {exc}") from exc
