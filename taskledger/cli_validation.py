from __future__ import annotations

import json
from typing import Annotated

import typer

from taskledger.api.validation import (
    append_validation_record,
    list_validation_records,
    remove_validation_records,
    summarize_validation_records,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_validation_commands(app: typer.Typer) -> None:
    @app.command("list")
    def validation_list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        records = list_validation_records(state.cwd)
        emit_payload(
            ctx,
            records,
            human=human_list(
                "VALIDATION",
                [
                    "  ".join(
                        part
                        for part in (
                            str(record["id"]),
                            str(record["kind"]),
                            str(record.get("status") or "-"),
                            f"{record['project_item_ref']}->{record['memory_ref']}",
                        )
                        if part
                    )
                    for record in records
                ],
            ),
        )

    @app.command("add")
    def validation_add_command(
        ctx: typer.Context,
        project_item_ref: Annotated[
            str,
            typer.Option("--item", help="Project item ref."),
        ],
        memory_ref: Annotated[
            str,
            typer.Option("--memory", help="Validation memory ref."),
        ],
        kind: Annotated[
            str,
            typer.Option("--kind", help="Validation record kind."),
        ],
        run_id: Annotated[
            str | None,
            typer.Option("--run-id", help="Associated run id."),
        ] = None,
        status: Annotated[
            str | None,
            typer.Option("--status", help="Validation status."),
        ] = None,
        verdict: Annotated[
            str | None,
            typer.Option("--verdict", help="Validation verdict."),
        ] = None,
        notes: Annotated[
            str | None,
            typer.Option("--notes", help="Validation notes."),
        ] = None,
        source: Annotated[
            str | None,
            typer.Option(
                "--source",
                help="Optional JSON object describing the source.",
            ),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = append_validation_record(
                state.cwd,
                project_item_ref=project_item_ref,
                memory_ref=memory_ref,
                kind=kind,
                run_id=run_id,
                status=status,
                verdict=verdict,
                notes=notes,
                source=_parse_source(source),
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record,
            human=f"added validation record {record['id']}",
        )

    @app.command("remove")
    def validation_remove_command(
        ctx: typer.Context,
        ids: Annotated[
            list[str],
            typer.Option("--id", help="Validation record id to remove. Repeatable."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        removed = remove_validation_records(state.cwd, ids=set(ids))
        emit_payload(
            ctx,
            removed,
            human=human_list(
                "REMOVED VALIDATION",
                [str(record["id"]) for record in removed],
            ),
        )

    @app.command("summary")
    def validation_summary_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        payload = summarize_validation_records(state.cwd)
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                "VALIDATION SUMMARY",
                [
                    ("count", payload["count"]),
                    ("by_kind", _format_counts(payload["by_kind"])),
                    ("by_status", _format_counts(payload["by_status"])),
                ],
            ),
        )


def _parse_source(source: str | None) -> dict[str, object] | None:
    if source is None:
        return None
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Validation source must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LaunchError("Validation source must decode to a JSON object.")
    return parsed


def _format_counts(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    return ", ".join(f"{key}={count}" for key, count in sorted(value.items()))
