"""Actor identity CLI commands."""

from __future__ import annotations

import json

import typer

from taskledger.cli_common import emit_payload
from taskledger.services.actors import resolve_actor, resolve_harness

app = typer.Typer(help="Actor and harness identity commands.")


@app.command(name="whoami")
def whoami_cmd(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show current actor and harness identity."""
    actor = resolve_actor()
    harness = resolve_harness()

    payload = {
        "kind": "taskledger_actor_identity",
        "actor": actor.to_dict(),
        "harness": harness.to_dict(),
    }

    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        human_lines = [
            f"Actor: {actor.actor_type}:{actor.actor_name}",
        ]
        if actor.role:
            human_lines.append(f"Role: {actor.role}")
        if actor.tool:
            human_lines.append(f"Tool: {actor.tool}")
        if actor.session_id:
            human_lines.append(f"Session: {actor.session_id}")
        human_lines.extend(
            [
                f"Harness: {harness.name} ({harness.kind})",
            ]
        )
        if harness.session_id:
            human_lines.append(f"Harness Session: {harness.session_id}")
        typer.echo("\n".join(human_lines))

    emit_payload(ctx, payload, result_type="actor_identity")
