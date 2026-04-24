from __future__ import annotations

from pathlib import Path
from typing import Callable
from typing import Annotated

import typer

from taskledger.api.memories import (
    append_memory_body,
    create_memory_entry,
    delete_memory_entry,
    list_memories,
    prepend_memory_body,
    rename_memory_entry,
    replace_memory_body,
    retag_memory,
    show_memory_with_body,
)
from taskledger.api.types import Memory
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
    read_text_input,
)
from taskledger.errors import LaunchError


def register_memory_commands(app: typer.Typer) -> None:
    @app.command("create")
    def memory_create_command(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(..., help="Memory name.")],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Optional body text."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read body text from a file."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        body = None
        if text is not None or from_file is not None:
            body = read_text_input(text=text, from_file=from_file)
        memory = create_memory_entry(state.cwd, name=name, body=body)
        emit_payload(
            ctx,
            memory.to_dict(),
            human=f"created memory {memory.id}: {memory.name}",
        )

    @app.command("list")
    def memory_list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        memories = list_memories(state.cwd)
        emit_payload(
            ctx,
            [memory.to_dict() for memory in memories],
            human=human_list(
                "MEMORIES",
                [
                    f"{memory.id}  {memory.slug}  {memory.summary or ''}".rstrip()
                    for memory in memories
                ],
            ),
        )

    @app.command("show")
    def memory_show_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory, body = show_memory_with_body(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        payload = {**memory.to_dict(), "body": body}
        emit_payload(
            ctx,
            payload,
            human="\n\n".join(
                [
                    human_kv(
                        f"MEMORY {memory.id}",
                        [
                            ("name", memory.name),
                            ("slug", memory.slug),
                            ("summary", memory.summary),
                        ],
                    ),
                    body.rstrip(),
                ]
            ).rstrip(),
        )

    @app.command("write")
    def memory_write_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Replacement body text."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read replacement body text from a file."),
        ] = None,
    ) -> None:
        _emit_memory_update(
            ctx,
            ref,
            text=text,
            from_file=from_file,
            update_func=replace_memory_body,
            verb="updated",
        )

    @app.command("append")
    def memory_append_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Text to append."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read appended text from a file."),
        ] = None,
    ) -> None:
        _emit_memory_update(
            ctx,
            ref,
            text=text,
            from_file=from_file,
            update_func=append_memory_body,
            verb="appended to",
        )

    @app.command("prepend")
    def memory_prepend_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
        text: Annotated[
            str | None,
            typer.Option("--text", help="Text to prepend."),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from-file", help="Read prepended text from a file."),
        ] = None,
    ) -> None:
        _emit_memory_update(
            ctx,
            ref,
            text=text,
            from_file=from_file,
            update_func=prepend_memory_body,
            verb="prepended to",
        )

    @app.command("rename")
    def memory_rename_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
        new_name: Annotated[
            str,
            typer.Option("--new-name", help="New memory name."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory, body = rename_memory_entry(state.cwd, ref, new_name=new_name)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {**memory.to_dict(), "body": body},
            human=f"renamed memory {memory.id}",
        )

    @app.command("retag")
    def memory_retag_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
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
            memory, body = retag_memory(
                state.cwd,
                ref,
                add_tags=tuple(add_tags or ()),
                remove_tags=tuple(remove_tags or ()),
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            {**memory.to_dict(), "body": body},
            human=f"retagged memory {memory.id}",
        )

    @app.command("delete")
    def memory_delete_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Memory ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            memory = delete_memory_entry(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            memory.to_dict(),
            human=f"deleted memory {memory.id}",
        )


def _emit_memory_update(
    ctx: typer.Context,
    ref: str,
    *,
    text: str | None,
    from_file: Path | None,
    update_func: Callable[..., tuple[Memory, str]],
    verb: str,
) -> None:
    state = cli_state_from_context(ctx)
    body = read_text_input(text=text, from_file=from_file)
    try:
        memory, updated_body = update_func(state.cwd, ref, body)
    except LaunchError as exc:
        emit_error(ctx, str(exc))
        raise typer.Exit(code=1) from exc
    emit_payload(
        ctx,
        {**memory.to_dict(), "body": updated_body},
        human=f"{verb} memory {memory.id}",
    )
