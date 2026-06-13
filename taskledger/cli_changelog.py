from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, cast

import typer

from taskledger.api.changelog import (
    add_changelog_entry,
    add_many_changelog_entries,
    build_changelog_prompt,
    import_changelog_entry_file,
    lint_changelog_entries,
    list_changelog_entries,
    update_changelog_entry,
)
from taskledger.cli_common import (
    TaskOption,
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    launch_error_exit_code,
    render_json,
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


def _lint_issue_lines(payload: dict[str, object]) -> list[str]:
    lines: list[str] = []
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return lines
    for item in issues:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "warning")).upper()
        label = "WARN" if severity == "WARNING" else "ERROR"
        entry_id = str(item.get("entry_id") or "-")
        field = str(item.get("field") or "-")
        message = str(item.get("message") or "")
        lines.append(f"{label:<5} {entry_id:<9} {field:<8} {message}")
    return lines


def _render_validation_error(exc: LaunchError) -> str | None:
    details = exc.details
    issues = details.get("issues")
    if not isinstance(issues, list) or not issues:
        return None
    lines = [str(exc)]
    for item in issues:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "warning"))
        field = str(item.get("field", "summary"))
        index = item.get("index")
        message = str(item.get("message", ""))
        if isinstance(index, int):
            lines.append(f"- entry[{index}] {severity} {field}: {message}")
        else:
            lines.append(f"- {severity} {field}: {message}")
    return "\n".join(lines)


def _load_batch_entries(path: Path) -> list[dict[str, object]]:
    from taskledger.storage.yaml_store import load_yaml_object

    raw = load_yaml_object(path, "batch file")
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise LaunchError("Batch file must define `entries` as a list.")
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(entries, start=1):
        if not isinstance(item, dict):
            raise LaunchError(f"entries[{index}] must be a mapping.")
        normalized.append(cast(dict[str, object], item))
    return normalized


def register_changelog_commands(app: typer.Typer) -> None:  # noqa: C901
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
        dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
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
                dry_run=dry_run,
            )
        except LaunchError as exc:
            rendered = None if state.json_output else _render_validation_error(exc)
            if rendered is None:
                emit_error(ctx, exc)
            else:
                typer.echo(rendered, err=True)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload: dict[str, object] = {
            "kind": "changelog_entry_preview" if dry_run else "changelog_entry",
            "entry": entry.to_dict(),
            "issues": [],
            "written": not dry_run,
        }
        emit_payload(
            ctx,
            payload,
            human=(
                "validated changelog entry preview "
                f"{entry.entry_id} for {entry.task_id}"
                if dry_run
                else f"added changelog entry {entry.entry_id} for {entry.task_id}"
            ),
        )

    @app.command("update")
    def update_command(
        ctx: typer.Context,
        entry_id: Annotated[str, typer.Argument(..., help="Changelog entry id.")],
        task_ref: TaskOption = None,
        category: Annotated[str | None, typer.Option("--category")] = None,
        summary: Annotated[str | None, typer.Option("--summary")] = None,
        body: Annotated[str | None, typer.Option("--body")] = None,
        status: Annotated[str | None, typer.Option("--status")] = None,
        release_version: Annotated[
            str | None, typer.Option("--release-version")
        ] = None,
        audience: Annotated[str | None, typer.Option("--audience")] = None,
        scopes: Annotated[list[str] | None, typer.Option("--scope")] = None,
        source_run_id: Annotated[str | None, typer.Option("--source-run-id")] = None,
        source_kind: Annotated[str | None, typer.Option("--source-kind")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            entry = update_changelog_entry(
                state.cwd,
                task.id,
                entry_id,
                category=category,
                summary=summary,
                body=body,
                release_version=release_version,
                status=status,
                audience=audience,
                scopes=tuple(scopes) if scopes is not None else None,
                source_run_id=source_run_id,
                source_kind=source_kind,
            )
        except LaunchError as exc:
            rendered = None if state.json_output else _render_validation_error(exc)
            if rendered is None:
                emit_error(ctx, exc)
            else:
                typer.echo(rendered, err=True)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload = {
            "kind": "changelog_entry",
            "entry": entry.to_dict(),
            "updated": True,
            "issues": [],
        }
        emit_payload(
            ctx,
            payload,
            human=f"updated changelog entry {entry.entry_id} for {entry.task_id}",
        )

    @app.command("add-many")
    def add_many_command(
        ctx: typer.Context,
        source_file: Annotated[
            Path,
            typer.Option("--file", exists=True, dir_okay=False),
        ],
        task_ref: TaskOption = None,
        dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            entries = _load_batch_entries(source_file)
            payload = add_many_changelog_entries(
                state.cwd,
                task.id,
                entries,
                dry_run=dry_run,
                fail_on_warning=True,
            )
        except LaunchError as exc:
            rendered = None if state.json_output else _render_validation_error(exc)
            if rendered is None:
                emit_error(ctx, exc)
            else:
                typer.echo(rendered, err=True)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        emit_payload(
            ctx,
            payload,
            human=(
                f"validated changelog batch preview for {payload['task_id']}: "
                f"{payload['entry_count']} entries"
                if dry_run
                else f"added changelog batch for {payload['task_id']}: "
                f"{payload['entry_count']} entries"
            ),
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
            lint_payload = exc.details if isinstance(exc.details, dict) else None
            if (
                not state.json_output
                and isinstance(lint_payload, dict)
                and lint_payload.get("kind") == "changelog_lint"
            ):
                summary = cast(dict[str, object], lint_payload.get("summary") or {})
                errors = _summary_count(summary, "errors")
                warnings = _summary_count(summary, "warnings")
                human_lines = [
                    (
                        f"linted changelog entries: {errors} error(s), "
                        f"{warnings} warning(s), "
                        f"{lint_payload.get('entry_count', 0)} entries"
                    )
                ]
                human_lines.extend(_lint_issue_lines(lint_payload))
                typer.echo("\n".join(human_lines), err=True)
            else:
                emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        summary = cast(dict[str, object], payload.get("summary") or {})
        errors = _summary_count(summary, "errors")
        warnings = _summary_count(summary, "warnings")
        human_lines = [
            (
                f"linted changelog entries: {errors} error(s), "
                f"{warnings} warning(s), {payload.get('entry_count', 0)} entries"
            )
        ]
        human_lines.extend(_lint_issue_lines(payload))
        emit_payload(
            ctx,
            payload,
            human="\n".join(human_lines),
        )

    @app.command("prompt")
    def prompt_command(
        ctx: typer.Context,
        task_ref: TaskOption = None,
        format_name: Annotated[str, typer.Option("--format")] = "markdown",
        output: Annotated[Path | None, typer.Option("--output")] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            task = resolve_cli_task(state.cwd, task_ref)
            prompt = build_changelog_prompt(state.cwd, task.id, format_name=format_name)
        except LaunchError as exc:
            emit_error(ctx, exc)
            raise typer.Exit(code=launch_error_exit_code(exc)) from exc
        payload: dict[str, object] = {
            "kind": "changelog_prompt",
            "task_ref": task_ref,
            "format": format_name,
            "prompt": prompt,
        }
        if output is not None:
            rendered = (
                render_json(prompt)
                if isinstance(prompt, dict)
                else prompt
                if isinstance(prompt, str)
                else json.dumps(prompt, indent=2, sort_keys=True) + "\n"
            )
            target = write_text_output(output, rendered)
            payload["output_path"] = str(target)
            emit_payload(
                ctx,
                payload,
                human=f"wrote changelog prompt to {target}",
            )
            return
        human = prompt if isinstance(prompt, str) else render_json(prompt)
        emit_payload(ctx, payload, human=human)
