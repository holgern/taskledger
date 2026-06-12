from __future__ import annotations

from pathlib import Path
from typing import Annotated, cast

import typer

from taskledger.api.changelog import (
    add_changelog_entry,
    build_changelog_prompt,
    import_changelog_entry_file,
    lint_changelog_entries,
    list_changelog_entries,
)
from taskledger.cli_common import (
    TaskOption,
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    launch_error_exit_code,
    resolve_cli_task,
    write_text_output,
)
from taskledger.domain.models import CHANGELOG_STATUSES
from taskledger.errors import LaunchError
from taskledger.storage.task_store import (
    changelog_entry_markdown_path,
    resolve_v2_paths,
)


def _summary_count(summary: dict[str, object], key: str) -> int:
    value = summary.get(key)
    return value if isinstance(value, int) else 0


def register_changelog_commands(app: typer.Typer) -> None:
    @app.command("add")
    def add_command(
        ctx: typer.Context,
        category: Annotated[str, typer.Option("--category")],
        summary: Annotated[str, typer.Option("--summary")],
        task_ref: TaskOption = None,
        body: Annotated[str, typer.Option("--body")] = "",
        release_version: Annotated[
            str | None, typer.Option("--release-version")
        ] = None,
        status: Annotated[str, typer.Option("--status")] = "accepted",
        audience: Annotated[str | None, typer.Option("--audience")] = None,
        scopes: Annotated[list[str] | None, typer.Option("--scope")] = None,
        source_run_id: Annotated[str | None, typer.Option("--source-run-id")] = None,
        source_kind: Annotated[str | None, typer.Option("--source-kind")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            entry = add_changelog_entry(
                state.cwd,
                task.id,
                category=category,
                summary=summary,
                body=body,
                release_version=release_version,
                status=status,
                audience=audience,
                scopes=tuple(scopes or ()),
                source_run_id=source_run_id,
                source_kind=source_kind,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = {"kind": "changelog_entry", "entry": entry.to_dict()}
        emit_payload(
            ctx,
            payload,
            human=f"added changelog entry {entry.entry_id} for {entry.task_id}",
        )

    @app.command("list")
    def list_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        version: Annotated[str | None, typer.Option("--version")] = None,
        include_status: Annotated[
            list[str] | None, typer.Option("--include-status")
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            resolved_task_ref = task_ref
            if resolved_task_ref is None and version is None:
                resolved_task_ref = resolve_cli_task(state.cwd, None).id
            entries = list_changelog_entries(
                state.cwd,
                task_ref=resolved_task_ref,
                version=version,
                include_statuses=tuple(include_status or ("accepted",)),
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = {
            "kind": "changelog_entry_list",
            "task_ref": task_ref,
            "version": version,
            "entries": [entry.to_dict() for entry in entries],
            "count": len(entries),
        }
        human_lines = ["CHANGELOG ENTRIES"]
        if not entries:
            human_lines.append("(empty)")
        else:
            for entry in entries:
                human_lines.append(
                    f"{entry.entry_id}  {entry.task_id}  {entry.status}  "
                    f"{entry.category}  {entry.summary}"
                )
        emit_payload(ctx, payload, human="\n".join(human_lines))

    @app.command("show")
    def show_command(
        ctx: typer.Context,
        entry_id: Annotated[str, typer.Argument(..., help="Changelog entry id.")],
        task_ref: TaskOption = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            entries = list_changelog_entries(
                state.cwd,
                task_ref=task.id,
                include_statuses=CHANGELOG_STATUSES,
            )
            entry = next(
                (candidate for candidate in entries if candidate.entry_id == entry_id),
                None,
            )
            if entry is None:
                raise LaunchError(f"Changelog entry not found: {entry_id}")
            path = changelog_entry_markdown_path(
                resolve_v2_paths(state.cwd),
                entry.task_id,
                entry.entry_id,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = {
            "kind": "changelog_entry",
            "entry": entry.to_dict(),
            "path": str(path),
        }
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                f"CHANGELOG ENTRY {entry.entry_id}",
                [
                    ("task_id", entry.task_id),
                    ("status", entry.status),
                    ("category", entry.category),
                    ("summary", entry.summary),
                    ("release_version", entry.release_version),
                    ("source_run_id", entry.source_run_id),
                    ("path", str(path)),
                ],
            ),
        )

    @app.command("import")
    def import_command(
        ctx: typer.Context,
        source: Annotated[Path, typer.Argument(..., exists=True, dir_okay=False)],
        task_ref: TaskOption = None,
        replace: Annotated[bool, typer.Option("--replace")] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            entry = import_changelog_entry_file(
                state.cwd,
                task.id,
                source,
                replace=replace,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = {"kind": "changelog_entry", "entry": entry.to_dict()}
        emit_payload(
            ctx,
            payload,
            human=f"imported changelog entry {entry.entry_id} for {entry.task_id}",
        )

    @app.command("lint")
    def lint_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        version: Annotated[str | None, typer.Option("--version")] = None,
        strict: Annotated[bool, typer.Option("--strict")] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            resolved_task_ref = task_ref
            if resolved_task_ref is None and version is None:
                resolved_task_ref = resolve_cli_task(state.cwd, None).id
            payload = lint_changelog_entries(
                state.cwd,
                task_ref=resolved_task_ref,
                version=version,
                strict=strict,
            )
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        summary = cast(dict[str, object], payload.get("summary") or {})
        errors = _summary_count(summary, "errors")
        warnings = _summary_count(summary, "warnings")
        emit_payload(
            ctx,
            payload,
            human=(
                f"linted changelog entries: {errors} error(s), "
                f"{warnings} warning(s), {payload.get('entry_count', 0)} entries"
            ),
        )

    @app.command("prompt")
    def prompt_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        output: Annotated[Path | None, typer.Option("--output")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            prompt = build_changelog_prompt(state.cwd, task.id)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload: dict[str, object] = {
            "kind": "changelog_prompt",
            "task_ref": task_ref,
            "prompt": prompt,
        }
        if output is not None:
            target = write_text_output(output, prompt)
            payload["output_path"] = str(target)
            emit_payload(
                ctx,
                payload,
                human=f"wrote changelog prompt to {target}",
            )
            return
        emit_payload(ctx, payload, human=prompt)
