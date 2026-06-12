from __future__ import annotations

import typer

from taskledger.cli_common import (
    CLIState,
    emit_error,
    emit_payload,
    launch_error_exit_code,
)
from taskledger.errors import LaunchError
from taskledger.refs import parse_taskledger_ref

ref_app = typer.Typer(add_completion=False, help="Parse and render resource refs.")


def _ref_payload(
    local_id: str,
    ledger: str,
    kind: str,
    number: int,
) -> dict[str, object]:
    return {
        "ok": True,
        "kind": "resource_ref",
        "local_id": local_id,
        "global_ref": f"{ledger}:{local_id}",
        "file_ref": f"{ledger}-{local_id}",
        "ledger": ledger,
        "resource_kind": kind,
        "number": number,
    }


def _emit_ref(ctx: typer.Context, value: str) -> None:
    state = ctx.obj
    assert isinstance(state, CLIState)
    try:
        parsed = parse_taskledger_ref(state.cwd, value)
    except LaunchError as exc:
        emit_error(ctx, exc)
        raise typer.Exit(code=launch_error_exit_code(exc)) from exc
    if parsed.ledger is None:
        raise LaunchError(
            f"Invalid taskledger resource ref {value!r}: missing ledger code"
        )
    payload = _ref_payload(
        parsed.local_id,
        parsed.ledger,
        parsed.kind,
        parsed.number,
    )
    lines = [
        "RESOURCE REF",
        f"  local id:   {payload['local_id']}",
        f"  global ref: {payload['global_ref']}",
        f"  file ref:   {payload['file_ref']}",
        f"  ledger:     {payload['ledger']}",
        f"  kind:       {payload['resource_kind']}",
        f"  number:     {payload['number']}",
    ]
    emit_payload(ctx, payload, human="\n".join(lines))


@ref_app.command("show")
def ref_show_command(
    ctx: typer.Context,
    value: str = typer.Argument(..., help="Resource ref or local id."),
) -> None:
    _emit_ref(ctx, value)


@ref_app.command("parse")
def ref_parse_command(
    ctx: typer.Context,
    value: str = typer.Argument(..., help="Resource ref or local id."),
) -> None:
    _emit_ref(ctx, value)
