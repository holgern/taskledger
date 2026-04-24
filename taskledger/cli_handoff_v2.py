"""Handoff protocol CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from taskledger.api.handoff import (
    list_all_handoffs,
    create_handoff,
    show_handoff,
    claim_handoff_api,
    close_handoff_api,
    cancel_handoff_api,
)
from taskledger.services.actors import resolve_actor, resolve_harness

app = typer.Typer(help="Handoff protocol commands.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    workspace_root: Path = typer.Option(..., "--workspace"),
    task_ref: str = typer.Argument(..., help="Task reference."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List handoffs for a task."""
    handoffs = list_all_handoffs(workspace_root, task_ref)
    
    if json_output:
        typer.echo(json.dumps({"kind": "handoff_list", "handoffs": handoffs}, indent=2))
    else:
        for h in handoffs:
            typer.echo(f"  {h['handoff_id']}: {h['status']} ({h['mode']})")


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    workspace_root: Path = typer.Option(..., "--workspace"),
    task_ref: str = typer.Argument(..., help="Task reference."),
    mode: str = typer.Option(..., "--mode", help="Handoff mode."),
    intended_actor: str | None = typer.Option(None, "--intended-actor"),
    summary: str | None = typer.Option(None, "--summary"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Create a new handoff."""
    result = create_handoff(
        workspace_root,
        task_ref,
        mode=mode,
        intended_actor_name=intended_actor,
        summary=summary,
    )
    
    if json_output:
        typer.echo(json.dumps({"kind": "handoff_created", "handoff": result}, indent=2))
    else:
        typer.echo(f"Created handoff: {result['handoff_id']}")


@app.command(name="show")
def show_cmd(
    ctx: typer.Context,
    workspace_root: Path = typer.Option(..., "--workspace"),
    task_ref: str = typer.Argument(..., help="Task reference."),
    handoff_ref: str = typer.Argument(..., help="Handoff reference."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show handoff details."""
    handoff = show_handoff(workspace_root, task_ref, handoff_ref)
    
    if json_output:
        typer.echo(json.dumps({"kind": "handoff", "handoff": handoff}, indent=2))
    else:
        typer.echo(json.dumps(handoff, indent=2))


@app.command(name="claim")
def claim_cmd(
    ctx: typer.Context,
    workspace_root: Path = typer.Option(..., "--workspace"),
    task_ref: str = typer.Argument(..., help="Task reference."),
    handoff_ref: str = typer.Argument(..., help="Handoff reference."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Claim a handoff."""
    actor = resolve_actor()
    harness = resolve_harness()
    
    updated = claim_handoff_api(workspace_root, task_ref, handoff_ref, actor=actor, harness=harness)
    
    if json_output:
        typer.echo(json.dumps({"kind": "handoff_claimed", "handoff": updated}, indent=2))
    else:
        typer.echo(f"Claimed handoff: {updated['handoff_id']}")


@app.command(name="close")
def close_cmd(
    ctx: typer.Context,
    workspace_root: Path = typer.Option(..., "--workspace"),
    task_ref: str = typer.Argument(..., help="Task reference."),
    handoff_ref: str = typer.Argument(..., help="Handoff reference."),
    reason: str | None = typer.Option(None, "--reason", help="Closure reason."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Close a handoff."""
    updated = close_handoff_api(workspace_root, task_ref, handoff_ref, reason=reason)
    
    if json_output:
        typer.echo(json.dumps({"kind": "handoff_closed", "handoff": updated}, indent=2))
    else:
        typer.echo(f"Closed handoff: {updated['handoff_id']}")


@app.command(name="cancel")
def cancel_cmd(
    ctx: typer.Context,
    workspace_root: Path = typer.Option(..., "--workspace"),
    task_ref: str = typer.Argument(..., help="Task reference."),
    handoff_ref: str = typer.Argument(..., help="Handoff reference."),
    reason: str | None = typer.Option(None, "--reason", help="Cancellation reason."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Cancel a handoff."""
    updated = cancel_handoff_api(workspace_root, task_ref, handoff_ref, reason=reason)
    
    if json_output:
        typer.echo(json.dumps({"kind": "handoff_cancelled", "handoff": updated}, indent=2))
    else:
        typer.echo(f"Cancelled handoff: {updated['handoff_id']}")

