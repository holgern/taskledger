from __future__ import annotations

from typing import Annotated

import typer

from taskledger.api.contexts import (
    create_context_entry,
    delete_context_entry,
    list_context_entries,
    rename_context_entry,
    show_context_entry,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_context_commands(app: typer.Typer) -> None:
    @app.command("save")
    def context_save_command(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(..., help="Context name.")],
        memory_refs: Annotated[
            list[str] | None,
            typer.Option("--memory", help="Memory ref to include. Repeatable."),
        ] = None,
        file_refs: Annotated[
            list[str] | None,
            typer.Option("--file", help="File ref to include. Repeatable."),
        ] = None,
        directory_refs: Annotated[
            list[str] | None,
            typer.Option("--dir", help="Directory ref to include. Repeatable."),
        ] = None,
        item_refs: Annotated[
            list[str] | None,
            typer.Option("--item", help="Work item ref to include. Repeatable."),
        ] = None,
        inline_texts: Annotated[
            list[str] | None,
            typer.Option("--inline", help="Inline text to include. Repeatable."),
        ] = None,
        loop_latest_refs: Annotated[
            list[str] | None,
            typer.Option(
                "--loop-latest",
                help="Loop artifact ref to include. Repeatable.",
            ),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        entry = create_context_entry(
            state.cwd,
            name=name,
            memory_refs=tuple(memory_refs or ()),
            file_refs=tuple(file_refs or ()),
            directory_refs=tuple(directory_refs or ()),
            item_refs=tuple(item_refs or ()),
            inline_texts=tuple(inline_texts or ()),
            loop_latest_refs=tuple(loop_latest_refs or ()),
        )
        emit_payload(
            ctx,
            entry.to_dict(),
            human=f"saved context {entry.slug}",
        )

    @app.command("list")
    def context_list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        entries = list_context_entries(state.cwd)
        emit_payload(
            ctx,
            [entry.to_dict() for entry in entries],
            human=human_list(
                "CONTEXTS",
                [
                    f"{entry.slug}  memories={len(entry.memory_refs)}  "
                    f"files={len(entry.file_refs)}  "
                    f"dirs={len(entry.directory_refs)}  "
                    f"items={len(entry.item_refs)}"
                    for entry in entries
                ],
            ),
        )

    @app.command("show")
    def context_show_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Context ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            entry = show_context_entry(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            entry.to_dict(),
            human=human_kv(
                f"CONTEXT {entry.slug}",
                [
                    ("memories", ", ".join(entry.memory_refs) or "-"),
                    ("files", ", ".join(entry.file_refs) or "-"),
                    ("dirs", ", ".join(entry.directory_refs) or "-"),
                    ("items", ", ".join(entry.item_refs) or "-"),
                    ("summary", entry.summary),
                ],
            ),
        )

    @app.command("rename")
    def context_rename_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Context ref.")],
        new_name: Annotated[
            str,
            typer.Option("--new-name", help="New context name."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            entry = rename_context_entry(state.cwd, ref, new_name=new_name)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            entry.to_dict(),
            human=f"renamed context {entry.slug}",
        )

    @app.command("delete")
    def context_delete_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Context ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            entry = delete_context_entry(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            entry.to_dict(),
            human=f"deleted context {entry.slug}",
        )
