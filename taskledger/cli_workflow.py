from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.workflows import (
    allowed_stage_transitions,
    approve_stage,
    assign_item_workflow,
    describe_item_workflow,
    enter_stage,
    list_workflows,
    resolve_workflow,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_workflow_commands(app: typer.Typer) -> None:
    @app.command("list")
    def workflow_list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        workflows = list_workflows(state.cwd)
        emit_payload(
            ctx,
            [workflow.to_dict() for workflow in workflows],
            human=human_list(
                "WORKFLOWS",
                [
                    f"{workflow.workflow_id}  {workflow.version}  "
                    f"stages={len(workflow.stages)}"
                    + ("  default" if workflow.default_for_items else "")
                    for workflow in workflows
                ],
            ),
        )

    @app.command("show")
    def workflow_show_command(
        ctx: typer.Context,
        workflow_id: Annotated[str, typer.Argument(..., help="Workflow id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            workflow = resolve_workflow(state.cwd, workflow_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            workflow.to_dict(),
            human=human_kv(
                f"WORKFLOW {workflow.workflow_id}",
                [
                    ("name", workflow.name),
                    ("version", workflow.version),
                    ("default_for_items", workflow.default_for_items),
                    ("stages", ", ".join(stage.stage_id for stage in workflow.stages)),
                ],
            ),
        )

    @app.command("assign")
    def workflow_assign_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        workflow_id: Annotated[str, typer.Argument(..., help="Workflow id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            item = assign_item_workflow(state.cwd, item_ref, workflow_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            item.to_dict(),
            human=f"assigned workflow {item.workflow_id} to {item.id}",
        )

    @app.command("state")
    def workflow_state_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = describe_item_workflow(state.cwd, item_ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        workflow = payload["workflow"]
        current_state = payload["state"]
        assert isinstance(workflow, dict)
        assert isinstance(current_state, dict)
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                f"WORKFLOW STATE {current_state['item_ref']}",
                [
                    ("workflow", workflow["workflow_id"]),
                    ("current_stage", current_state["current_stage_id"]),
                    ("workflow_status", current_state["workflow_status"]),
                    ("stage_status", current_state["stage_status"]),
                    ("allowed_next", ", ".join(current_state["allowed_next_stages"])),
                    ("blocking_reasons", ", ".join(current_state["blocking_reasons"])),
                ],
            ),
        )

    @app.command("stages")
    def workflow_stages_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            payload = describe_item_workflow(state.cwd, item_ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        stages = payload["stages"]
        assert isinstance(stages, list)
        emit_payload(
            ctx,
            stages,
            human=human_list(
                "WORKFLOW STAGES",
                [
                    f"{stage['stage_id']}  {stage['stage_status']}  "
                    f"allowed={stage['allowed']}"
                    for stage in stages
                    if isinstance(stage, dict)
                ],
            ),
        )

    @app.command("transitions")
    def workflow_transitions_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            transitions = allowed_stage_transitions(state.cwd, item_ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"item_ref": item_ref, "allowed_next_stages": list(transitions)},
            human=human_list("ALLOWED STAGES", list(transitions)),
        )

    @app.command("enter")
    def workflow_enter_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = enter_stage(state.cwd, item_ref, stage_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record.to_dict(),
            human=f"entered workflow stage {stage_id} for {item_ref}",
        )

    @app.command("approve-stage")
    def workflow_approve_stage_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = approve_stage(state.cwd, item_ref, stage_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record.to_dict(),
            human=f"approved workflow stage {stage_id} for {item_ref}",
        )
