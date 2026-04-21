from __future__ import annotations

from typing import Annotated, cast

import typer

from taskledger.api.composition import (
    SelectionRequest,
    build_compose_payload,
    build_sources,
    compose_bundle,
    expand_selection,
    repo_refs_for_sources,
)
from taskledger.api.runtime_support import get_effective_project_config
from taskledger.api.types import FileRenderMode, SourceBudget
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
)
from taskledger.errors import LaunchError


def register_compose_commands(app: typer.Typer) -> None:
    def _normalize_file_mode(raw: str) -> FileRenderMode:
        value = raw.strip().lower()
        if value not in {"content", "reference"}:
            raise LaunchError("File mode must be one of: content, reference.")
        return cast(FileRenderMode, value)

    @app.command("expand")
    def compose_expand_command(
        ctx: typer.Context,
        context_names: Annotated[
            list[str] | None,
            typer.Option("--context", help="Context names to expand. Repeatable."),
        ] = None,
        memory_refs: Annotated[
            list[str] | None,
            typer.Option("--memory", help="Memory refs to include. Repeatable."),
        ] = None,
        file_refs: Annotated[
            list[str] | None,
            typer.Option("--file", help="File refs to include. Repeatable."),
        ] = None,
        directory_refs: Annotated[
            list[str] | None,
            typer.Option("--dir", help="Directory refs to include. Repeatable."),
        ] = None,
        item_refs: Annotated[
            list[str] | None,
            typer.Option("--item", help="Item refs to include. Repeatable."),
        ] = None,
        inline_texts: Annotated[
            list[str] | None,
            typer.Option("--inline", help="Inline context snippets. Repeatable."),
        ] = None,
        loop_latest_refs: Annotated[
            list[str] | None,
            typer.Option("--loop-latest", help="Loop latest refs. Repeatable."),
        ] = None,
        item_memories: Annotated[
            bool,
            typer.Option(
                "--item-memories/--no-item-memories",
                help="Include item-linked memory bodies when expanding item refs.",
            ),
        ] = True,
        file_mode: Annotated[
            str,
            typer.Option("--file-mode", help="File render mode: content or reference."),
        ] = "content",
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            normalized_file_mode = _normalize_file_mode(file_mode)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        request = SelectionRequest(
            context_names=tuple(context_names or ()),
            memory_refs=tuple(memory_refs or ()),
            file_refs=tuple(file_refs or ()),
            directory_refs=tuple(directory_refs or ()),
            item_refs=tuple(item_refs or ()),
            inline_texts=tuple(inline_texts or ()),
            loop_latest_refs=tuple(loop_latest_refs or ()),
            include_item_memories=item_memories,
            file_render_mode=normalized_file_mode,
        )
        try:
            selection = expand_selection(state.cwd, request)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        payload = {
            "kind": "project_compose_expand",
            "request": request.to_dict(),
            "selection": selection.to_dict(),
        }
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                "COMPOSE EXPAND",
                [
                    ("contexts", len(selection.context_inputs)),
                    ("memories", len(selection.memory_inputs)),
                    ("files", len(selection.file_inputs)),
                    ("dirs", len(selection.directory_inputs)),
                    ("items", len(selection.item_inputs)),
                    ("inline", len(selection.inline_inputs)),
                    ("loop_artifacts", len(selection.loop_artifact_inputs)),
                ],
            ),
        )

    @app.command("bundle")
    def compose_bundle_command(
        ctx: typer.Context,
        prompt: Annotated[
            str,
            typer.Option("--prompt", help="Prompt text to compose."),
        ],
        context_names: Annotated[
            list[str] | None,
            typer.Option("--context", help="Context names to expand. Repeatable."),
        ] = None,
        memory_refs: Annotated[
            list[str] | None,
            typer.Option("--memory", help="Memory refs to include. Repeatable."),
        ] = None,
        file_refs: Annotated[
            list[str] | None,
            typer.Option("--file", help="File refs to include. Repeatable."),
        ] = None,
        directory_refs: Annotated[
            list[str] | None,
            typer.Option("--dir", help="Directory refs to include. Repeatable."),
        ] = None,
        item_refs: Annotated[
            list[str] | None,
            typer.Option("--item", help="Item refs to include. Repeatable."),
        ] = None,
        inline_texts: Annotated[
            list[str] | None,
            typer.Option("--inline", help="Inline context snippets. Repeatable."),
        ] = None,
        loop_latest_refs: Annotated[
            list[str] | None,
            typer.Option("--loop-latest", help="Loop latest refs. Repeatable."),
        ] = None,
        run_in_repo: Annotated[
            str | None,
            typer.Option("--run-in-repo", help="Execution repo hint."),
        ] = None,
        item_memories: Annotated[
            bool,
            typer.Option(
                "--item-memories/--no-item-memories",
                help="Include item-linked memory bodies when expanding item refs.",
            ),
        ] = True,
        file_mode: Annotated[
            str,
            typer.Option("--file-mode", help="File render mode: content or reference."),
        ] = "content",
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            normalized_file_mode = _normalize_file_mode(file_mode)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        request = SelectionRequest(
            context_names=tuple(context_names or ()),
            memory_refs=tuple(memory_refs or ()),
            file_refs=tuple(file_refs or ()),
            directory_refs=tuple(directory_refs or ()),
            item_refs=tuple(item_refs or ()),
            inline_texts=tuple(inline_texts or ()),
            loop_latest_refs=tuple(loop_latest_refs or ()),
            include_item_memories=item_memories,
            file_render_mode=normalized_file_mode,
        )
        try:
            config = get_effective_project_config(state.cwd)
            source_budget = SourceBudget(
                max_source_chars=config.default_source_max_chars,
                max_total_chars=config.default_total_source_max_chars,
                head_lines=config.default_source_head_lines,
                tail_lines=config.default_source_tail_lines,
            )
            selection = expand_selection(state.cwd, request)
            sources = build_sources(
                state.cwd,
                selection,
                default_context_order=config.default_context_order,
                include_item_memories=request.include_item_memories,
                file_render_mode=request.file_render_mode,
                source_budget=source_budget,
            )
            bundle = compose_bundle(prompt=prompt, sources=sources)
            payload = build_compose_payload(
                context_name=None,
                prompt=prompt,
                explicit_inputs={
                    "context_inputs": selection.context_inputs,
                    "memory_inputs": selection.memory_inputs,
                    "file_inputs": selection.file_inputs,
                    "directory_inputs": selection.directory_inputs,
                    "item_inputs": selection.item_inputs,
                    "inline_inputs": selection.inline_inputs,
                    "loop_artifact_inputs": selection.loop_artifact_inputs,
                },
                file_render_mode=request.file_render_mode,
                selected_repo_refs=repo_refs_for_sources(sources),
                run_in_repo=run_in_repo,
                source_budget=source_budget,
                bundle=bundle,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            payload,
            human=human_kv(
                "COMPOSE BUNDLE",
                [
                    ("sources", len(sources)),
                    ("repos", ", ".join(bundle.repo_refs) or "-"),
                    ("chars", len(bundle.composed_text)),
                    ("context_hash", bundle.content_hash),
                ],
            ),
        )
