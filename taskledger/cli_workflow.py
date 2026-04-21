from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.types import WorkflowDefinition
from taskledger.api.workflows import (
    allowed_stage_transitions,
    approve_stage,
    assign_item_workflow,
    can_enter_stage,
    default_workflow_id,
    delete_workflow_definition,
    describe_item_workflow,
    enter_stage,
    item_stage_records,
    latest_stage_record,
    list_workflows,
    mark_stage_failed,
    mark_stage_needs_review,
    mark_stage_running,
    mark_stage_succeeded,
    resolve_workflow,
    save_workflow_definition,
    set_default_workflow,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_workflow_commands(app: typer.Typer) -> None:  # noqa: C901
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

    @app.command("save")
    def workflow_save_command(
        ctx: typer.Context,
        from_file: Annotated[
            Path,
            typer.Option(
                "--from-file",
                help="JSON file containing a workflow definition object.",
            ),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            workflow = _workflow_from_file(from_file)
            saved = save_workflow_definition(state.cwd, workflow)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            saved.to_dict(),
            human=f"saved workflow {saved.workflow_id}",
        )

    @app.command("delete")
    def workflow_delete_command(
        ctx: typer.Context,
        workflow_id: Annotated[str, typer.Argument(..., help="Workflow id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            delete_workflow_definition(state.cwd, workflow_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"workflow_id": workflow_id, "deleted": True},
            human=f"deleted workflow {workflow_id}",
        )

    @app.command("default")
    def workflow_default_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        current = default_workflow_id(state.cwd)
        emit_payload(
            ctx,
            {"workflow_id": current},
            human=f"default workflow: {current or '-'}",
        )

    @app.command("set-default")
    def workflow_set_default_command(
        ctx: typer.Context,
        workflow_id: Annotated[str, typer.Argument(..., help="Workflow id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            workflow = set_default_workflow(state.cwd, workflow_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            workflow.to_dict(),
            human=f"set default workflow to {workflow.workflow_id}",
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

    @app.command("records")
    def workflow_records_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            records = item_stage_records(state.cwd, item_ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            [record.to_dict() for record in records],
            human=human_list(
                f"WORKFLOW RECORDS {item_ref}",
                [
                    f"{record.record_id}  {record.stage_id}  {record.status}"
                    for record in records
                ],
            ),
        )

    @app.command("latest")
    def workflow_latest_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = latest_stage_record(state.cwd, item_ref, stage_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        payload = record.to_dict() if record is not None else None
        emit_payload(
            ctx,
            payload,
            human=(
                f"no stage record for {item_ref} in {stage_id}"
                if record is None
                else f"latest {stage_id} record: {record.record_id}"
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

    @app.command("can-enter")
    def workflow_can_enter_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            allowed, blocking_reasons = can_enter_stage(state.cwd, item_ref, stage_id)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {
                "item_ref": item_ref,
                "stage_id": stage_id,
                "allowed": allowed,
                "blocking_reasons": list(blocking_reasons),
            },
            human=human_kv(
                f"CAN ENTER {item_ref} -> {stage_id}",
                [
                    ("allowed", allowed),
                    ("blocking_reasons", ", ".join(blocking_reasons) or "-"),
                ],
            ),
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

    @app.command("mark-running")
    def workflow_mark_running_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
        request_id: Annotated[
            str | None,
            typer.Option("--request-id", help="Execution request id."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = mark_stage_running(
                state.cwd,
                item_ref,
                stage_id,
                request_id=request_id,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record.to_dict(),
            human=f"marked stage {stage_id} running for {item_ref}",
        )

    @app.command("mark-succeeded")
    def workflow_mark_succeeded_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
        run_id: Annotated[
            str | None,
            typer.Option("--run-id", help="Associated run id."),
        ] = None,
        summary: Annotated[
            str | None,
            typer.Option("--summary", help="Optional output summary."),
        ] = None,
        save_target: Annotated[
            str | None,
            typer.Option("--save-target", help="Optional save target ref."),
        ] = None,
        validation_record_refs: Annotated[
            list[str] | None,
            typer.Option(
                "--validation-record",
                help="Validation record ref. Repeatable.",
            ),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = mark_stage_succeeded(
                state.cwd,
                item_ref,
                stage_id,
                run_id=run_id,
                summary=summary,
                save_target=save_target,
                validation_record_refs=tuple(validation_record_refs or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record.to_dict(),
            human=f"marked stage {stage_id} succeeded for {item_ref}",
        )

    @app.command("mark-failed")
    def workflow_mark_failed_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
        run_id: Annotated[
            str | None,
            typer.Option("--run-id", help="Associated run id."),
        ] = None,
        summary: Annotated[
            str | None,
            typer.Option("--summary", help="Optional failure summary."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = mark_stage_failed(
                state.cwd,
                item_ref,
                stage_id,
                run_id=run_id,
                summary=summary,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record.to_dict(),
            human=f"marked stage {stage_id} failed for {item_ref}",
        )

    @app.command("mark-needs-review")
    def workflow_mark_needs_review_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        stage_id: Annotated[str, typer.Argument(..., help="Workflow stage id.")],
        reason: Annotated[
            str | None,
            typer.Option("--reason", help="Review reason."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            record = mark_stage_needs_review(
                state.cwd,
                item_ref,
                stage_id,
                reason=reason,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            record.to_dict(),
            human=f"marked stage {stage_id} needs review for {item_ref}",
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


def _workflow_from_file(path: Path) -> WorkflowDefinition:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LaunchError(f"Failed to read workflow file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Workflow file must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LaunchError("Workflow file must contain a JSON object.")
    try:
        return WorkflowDefinition.from_dict(payload)
    except ValueError as exc:
        raise LaunchError(f"Invalid workflow definition payload: {exc}") from exc
