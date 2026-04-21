from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.items import (
    approve_item,
    close_item,
    create_item,
    list_items,
    next_action_payload,
    reopen_item,
    show_item,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
    read_text_input,
)
from taskledger.errors import LaunchError


def register_item_commands(app: typer.Typer) -> None:
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
                    ("target_repo", item.target_repo_ref),
                    ("description", item.description),
                ],
            ),
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
