from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.items import (
    approve_item,
    close_item,
    create_item,
    delete_item_memory,
    item_dossier,
    item_memory_refs,
    list_items,
    next_action_payload,
    read_item_memory_body,
    rename_item_memory,
    render_item_dossier_markdown,
    reopen_item,
    resolve_item_memory,
    retag_item_memory,
    show_item,
    update_item,
    write_item_memory_body,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
    read_text_input,
    write_text_output,
)
from taskledger.errors import LaunchError


def register_item_commands(app: typer.Typer) -> None:  # noqa: C901
    memory_app = typer.Typer(
        add_completion=False,
        help="Manage item-linked memories by role.",
    )
    app.add_typer(memory_app, name="memory")

    @app.command("create")
    def item_create_command(
        ctx: typer.Context,
        slug: Annotated[str, typer.Argument(..., help="Work item slug.")],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Work item description text."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read work item description from a file."),
        ] = None,
        title: Annotated[
            str | None,
            typer.Option("--title", help="Optional work item title."),
        ] = None,
        repo_refs: Annotated[
            list[str] | None,
            typer.Option("--repo", help="Associated repo ref. Repeatable."),
        ] = None,
        target_repo: Annotated[
            str | None,
            typer.Option("--target-repo", help="Preferred execution repo."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            item = create_item(
                state.cwd,
                slug=slug,
                description=read_text_input(text=text, from_file=from_file),
                title=title,
                repo_refs=tuple(repo_refs or ()),
                source_path=from_file,
                target_repo_ref=target_repo,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            item.to_dict(),
            human=f"created work item {item.id}: {item.slug}",
        )

    @app.command("list")
    def item_list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        items = list_items(state.cwd)
        emit_payload(
            ctx,
            [item.to_dict() for item in items],
            human=human_list(
                "WORK ITEMS",
                [
                    f"{item.id}  {item.status:<11}  {item.slug}  {item.title}"
                    for item in items
                ],
            ),
        )

    @app.command("show")
    def item_show_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            item = show_item(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            item.to_dict(),
            human=human_kv(
                f"ITEM {item.id}",
                [
                    ("slug", item.slug),
                    ("title", item.title),
                    ("status", item.status),
                    ("stage", item.stage),
                    ("workflow_status", item.workflow_status),
                    ("current_stage", item.current_stage_id),
                    ("stage_status", item.stage_status),
                    ("target_repo", item.target_repo_ref),
                    ("analysis_memory_ref", item.analysis_memory_ref),
                    ("state_memory_ref", item.state_memory_ref),
                    ("plan_memory_ref", item.plan_memory_ref),
                    ("implementation_memory_ref", item.implementation_memory_ref),
                    ("validation_memory_ref", item.validation_memory_ref),
                    ("save_target_ref", item.save_target_ref),
                    ("acceptance_criteria_count", len(item.acceptance_criteria)),
                    ("validation_checklist_count", len(item.validation_checklist)),
                    ("dependency_count", len(item.depends_on)),
                    ("linked_memory_count", len(item.linked_memories)),
                    ("linked_run_count", len(item.linked_runs)),
                    ("next_action", next_action_payload(item)["action"]),
                    ("next_action_actor", next_action_payload(item)["actor"]),
                    ("description", item.description),
                ],
            ),
        )

    @app.command("view")
    def item_view_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        roles: Annotated[
            list[str] | None,
            typer.Option("--role", help="Memory role to include. Repeatable."),
        ] = None,
        include_empty: Annotated[
            bool,
            typer.Option(
                "--include-empty/--skip-empty",
                help="Render empty memory sections as (empty).",
            ),
        ] = False,
        include_runs: Annotated[
            bool,
            typer.Option("--runs/--no-runs", help="Include related runs section."),
        ] = True,
        include_validation: Annotated[
            bool,
            typer.Option(
                "--validation/--no-validation",
                help="Include related validation section.",
            ),
        ] = True,
        include_workflow: Annotated[
            bool,
            typer.Option("--workflow/--no-workflow", help="Include workflow sections."),
        ] = True,
        include_contexts: Annotated[
            bool,
            typer.Option("--contexts/--no-contexts", help="Include context links."),
        ] = True,
        output: Annotated[
            Path | None,
            typer.Option(
                "--output",
                help="Write the rendered dossier text to a markdown file.",
            ),
        ] = None,
    ) -> None:
        _emit_item_dossier(
            ctx,
            ref,
            roles=tuple(roles or ()) or None,
            include_empty=include_empty,
            include_runs=include_runs,
            include_validation=include_validation,
            include_workflow=include_workflow,
            include_contexts=include_contexts,
            output=output,
        )

    @app.command("dossier")
    def item_dossier_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        roles: Annotated[
            list[str] | None,
            typer.Option("--role", help="Memory role to include. Repeatable."),
        ] = None,
        include_empty: Annotated[
            bool,
            typer.Option(
                "--include-empty/--skip-empty",
                help="Render empty memory sections as (empty).",
            ),
        ] = False,
        include_runs: Annotated[
            bool,
            typer.Option("--runs/--no-runs", help="Include related runs section."),
        ] = True,
        include_validation: Annotated[
            bool,
            typer.Option(
                "--validation/--no-validation",
                help="Include related validation section.",
            ),
        ] = True,
        include_workflow: Annotated[
            bool,
            typer.Option("--workflow/--no-workflow", help="Include workflow sections."),
        ] = True,
        include_contexts: Annotated[
            bool,
            typer.Option("--contexts/--no-contexts", help="Include context links."),
        ] = True,
        output: Annotated[
            Path | None,
            typer.Option(
                "--output",
                help="Write the rendered dossier text to a markdown file.",
            ),
        ] = None,
    ) -> None:
        _emit_item_dossier(
            ctx,
            ref,
            roles=tuple(roles or ()) or None,
            include_empty=include_empty,
            include_runs=include_runs,
            include_validation=include_validation,
            include_workflow=include_workflow,
            include_contexts=include_contexts,
            output=output,
        )

    @app.command("memories")
    def item_memories_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            item = show_item(state.cwd, ref)
            refs = item_memory_refs(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        payload = {"item_ref": item.id, "memories": refs}
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                f"ITEM MEMORIES {item.id}",
                [(role, value or "-") for role, value in refs.items()],
            ),
        )

    @app.command("update")
    def item_update_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        title: Annotated[
            str | None,
            typer.Option("--title", help="New item title."),
        ] = None,
        text: Annotated[
            str | None,
            typer.Option("--text", help="Replacement item description text."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option(
                "--from-file",
                help="Read replacement description text from file.",
            ),
        ] = None,
        notes: Annotated[
            str | None,
            typer.Option("--notes", help="Item notes text."),
        ] = None,
        owner: Annotated[
            str | None,
            typer.Option("--owner", help="Item owner."),
        ] = None,
        estimate: Annotated[
            str | None,
            typer.Option("--estimate", help="Item estimate."),
        ] = None,
        add_label: Annotated[
            list[str] | None,
            typer.Option("--add-label", help="Label to add. Repeatable."),
        ] = None,
        remove_label: Annotated[
            list[str] | None,
            typer.Option("--remove-label", help="Label to remove. Repeatable."),
        ] = None,
        add_dependency: Annotated[
            list[str] | None,
            typer.Option(
                "--add-dependency",
                help="Dependency item ref to add. Repeatable.",
            ),
        ] = None,
        remove_dependency: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-dependency",
                help="Dependency item ref to remove. Repeatable.",
            ),
        ] = None,
        add_repo: Annotated[
            list[str] | None,
            typer.Option("--add-repo", help="Repo ref to add. Repeatable."),
        ] = None,
        remove_repo: Annotated[
            list[str] | None,
            typer.Option("--remove-repo", help="Repo ref to remove. Repeatable."),
        ] = None,
        target_repo: Annotated[
            str | None,
            typer.Option("--target-repo", help="Set preferred execution repo."),
        ] = None,
        add_acceptance: Annotated[
            list[str] | None,
            typer.Option(
                "--add-acceptance",
                help="Acceptance criteria entry to add. Repeatable.",
            ),
        ] = None,
        remove_acceptance: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-acceptance",
                help="Acceptance criteria entry to remove. Repeatable.",
            ),
        ] = None,
        add_validation_check: Annotated[
            list[str] | None,
            typer.Option(
                "--add-validation-check",
                help="Validation checklist entry to add. Repeatable.",
            ),
        ] = None,
        remove_validation_check: Annotated[
            list[str] | None,
            typer.Option(
                "--remove-validation-check",
                help="Validation checklist entry to remove. Repeatable.",
            ),
        ] = None,
        save_target: Annotated[
            str | None,
            typer.Option("--save-target", help="Set the save target memory ref."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            description = None
            if text is not None or from_file is not None:
                description = read_text_input(text=text, from_file=from_file)
            item = update_item(
                state.cwd,
                ref,
                title=title,
                description=description,
                notes=notes,
                owner=owner,
                estimate=estimate,
                add_labels=tuple(add_label or ()),
                remove_labels=tuple(remove_label or ()),
                add_dependencies=tuple(add_dependency or ()),
                remove_dependencies=tuple(remove_dependency or ()),
                add_repo_refs=tuple(add_repo or ()),
                remove_repo_refs=tuple(remove_repo or ()),
                target_repo_ref=target_repo,
                add_acceptance=tuple(add_acceptance or ()),
                remove_acceptance=tuple(remove_acceptance or ()),
                add_validation_checks=tuple(add_validation_check or ()),
                remove_validation_checks=tuple(remove_validation_check or ()),
                save_target_ref=save_target,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            item.to_dict(),
            human=f"updated work item {item.id}",
        )

    @app.command("approve")
    def item_approve_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        _emit_lifecycle_result(ctx, ref, transform=approve_item, verb="approved")

    @app.command("reopen")
    def item_reopen_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        _emit_lifecycle_result(ctx, ref, transform=reopen_item, verb="reopened")

    @app.command("close")
    def item_close_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        _emit_lifecycle_result(ctx, ref, transform=close_item, verb="closed")

    @app.command("next")
    def item_next_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            item = show_item(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        payload = next_action_payload(item)
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                "ITEM NEXT",
                [
                    ("item", payload["item_ref"]),
                    ("action", payload["action"]),
                    ("actor", payload["actor"]),
                    ("reason", payload["reason"]),
                ],
            ),
        )

    @memory_app.command("show")
    def item_memory_show_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory = resolve_item_memory(state.cwd, item_ref, role)
            body = read_item_memory_body(state.cwd, item_ref, role)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"item_ref": item_ref, "role": role, **memory.to_dict(), "body": body},
            human="\n\n".join(
                [
                    human_kv(
                        f"ITEM MEMORY {item_ref}",
                        [
                            ("role", role),
                            ("memory", memory.id),
                            ("name", memory.name),
                            ("slug", memory.slug),
                            ("summary", memory.summary),
                        ],
                    ),
                    body.rstrip(),
                ]
            ).rstrip(),
        )

    @memory_app.command("write")
    def item_memory_write_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Replacement memory body text."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read replacement text from file."),
        ] = None,
    ) -> None:
        _emit_item_memory_update(
            ctx,
            item_ref,
            role,
            text=text,
            from_file=from_file,
            mode="replace",
            verb="updated",
        )

    @memory_app.command("append")
    def item_memory_append_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Text to append to the memory."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read appended text from file."),
        ] = None,
    ) -> None:
        _emit_item_memory_update(
            ctx,
            item_ref,
            role,
            text=text,
            from_file=from_file,
            mode="append",
            verb="appended to",
        )

    @memory_app.command("prepend")
    def item_memory_prepend_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Text to prepend to the memory."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read prepended text from file."),
        ] = None,
    ) -> None:
        _emit_item_memory_update(
            ctx,
            item_ref,
            role,
            text=text,
            from_file=from_file,
            mode="prepend",
            verb="prepended to",
        )

    @memory_app.command("rename")
    def item_memory_rename_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
        new_name: Annotated[
            str,
            typer.Option("--new-name", help="New memory name."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory = rename_item_memory(
                state.cwd,
                item_ref,
                role,
                new_name=new_name,
            )
            body = read_item_memory_body(state.cwd, item_ref, role)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"item_ref": item_ref, "role": role, **memory.to_dict(), "body": body},
            human=f"renamed {role} memory {memory.id} for {item_ref}",
        )

    @memory_app.command("retag")
    def item_memory_retag_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
        add_tags: Annotated[
            list[str] | None,
            typer.Option("--add-tag", help="Tag to add. Repeatable."),
        ] = None,
        remove_tags: Annotated[
            list[str] | None,
            typer.Option("--remove-tag", help="Tag to remove. Repeatable."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory = retag_item_memory(
                state.cwd,
                item_ref,
                role,
                add_tags=tuple(add_tags or ()),
                remove_tags=tuple(remove_tags or ()),
            )
            body = read_item_memory_body(state.cwd, item_ref, role)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"item_ref": item_ref, "role": role, **memory.to_dict(), "body": body},
            human=f"retagged {role} memory {memory.id} for {item_ref}",
        )

    @memory_app.command("delete")
    def item_memory_delete_command(
        ctx: typer.Context,
        item_ref: Annotated[str, typer.Argument(..., help="Work item ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Memory role."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory = delete_item_memory(state.cwd, item_ref, role)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {"item_ref": item_ref, "role": role, **memory.to_dict()},
            human=f"deleted {role} memory {memory.id} for {item_ref}",
        )


def _emit_lifecycle_result(
    ctx: typer.Context,
    ref: str,
    *,
    transform,
    verb: str,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        item = transform(state.cwd, ref)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(
        ctx,
        item.to_dict(),
        human=f"{verb} work item {item.id}",
    )


def _emit_item_memory_update(
    ctx: typer.Context,
    item_ref: str,
    role: str,
    *,
    text: str | None,
    from_file: Path | None,
    mode: str,
    verb: str,
) -> None:
    state = cli_state_from_context(ctx)
    body = read_text_input(text=text, from_file=from_file)
    try:
        memory = write_item_memory_body(
            state.cwd,
            item_ref,
            role,
            body,
            mode=mode,
        )
        updated_body = read_item_memory_body(state.cwd, item_ref, role)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(
        ctx,
        {"item_ref": item_ref, "role": role, **memory.to_dict(), "body": updated_body},
        human=f"{verb} {role} memory {memory.id} for {item_ref}",
    )


def _emit_item_dossier(
    ctx: typer.Context,
    ref: str,
    *,
    roles: tuple[str, ...] | None,
    include_empty: bool,
    include_runs: bool,
    include_validation: bool,
    include_workflow: bool,
    include_contexts: bool,
    output: Path | None,
) -> None:
    state = cli_state_from_context(ctx)
    try:
        dossier = item_dossier(
            state.cwd,
            ref,
            roles=roles,
            include_empty=include_empty,
            include_runs=include_runs,
            include_validation=include_validation,
            include_workflow=include_workflow,
            include_contexts=include_contexts,
        )
        rendered = render_item_dossier_markdown(dossier)
        output_path = None
        if output is not None:
            output_path = write_text_output(output, rendered)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    payload = dossier.to_dict()
    human = rendered
    if output_path is not None:
        human = f"{rendered.rstrip()}\n\nwrote dossier: {output_path}\n"
    emit_payload(ctx, payload, human=human)
