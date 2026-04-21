from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from taskledger.api.repos import (
    clear_default_execution_repo_entry,
    list_repos,
    register_repo,
    remove_repo_entry,
    set_default_execution_repo_entry,
    set_repo_role_entry,
    show_repo,
)
from taskledger.cli_common import (
    cli_state_from_context,
    emit_error,
    emit_payload,
    human_kv,
    human_list,
)
from taskledger.errors import LaunchError


def register_repo_commands(app: typer.Typer) -> None:
    @app.command("add")
    def repo_add_command(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(..., help="Repo name.")],
        path: Annotated[Path, typer.Option("--path", help="Repo path.")],
        kind: Annotated[
            str,
            typer.Option(
                "--kind",
                help="Repo kind: odoo, enterprise, custom, shared, generic.",
            ),
        ] = "generic",
        role: Annotated[
            str,
            typer.Option("--role", help="Repo role: read, write, or both."),
        ] = "read",
        branch: Annotated[
            str | None,
            typer.Option("--branch", help="Optional tracked branch."),
        ] = None,
        notes: Annotated[
            str | None,
            typer.Option("--notes", help="Optional notes."),
        ] = None,
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            repo = register_repo(
                state.cwd,
                name=name,
                path=path,
                kind=kind,
                role=role,
                branch=branch,
                notes=notes,
            )
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            repo.to_dict(),
            human=f"added repo {repo.name}",
        )

    @app.command("list")
    def repo_list_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        repos = list_repos(state.cwd)
        emit_payload(
            ctx,
            [repo.to_dict() for repo in repos],
            human=human_list(
                "REPOS",
                [
                    f"{repo.name}  {repo.kind}  role={repo.role}  path={repo.path}"
                    for repo in repos
                ],
            ),
        )

    @app.command("show")
    def repo_show_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Repo ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            repo = show_repo(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            repo.to_dict(),
            human=human_kv(
                f"REPO {repo.name}",
                [
                    ("kind", repo.kind),
                    ("role", repo.role),
                    ("path", repo.path),
                    ("branch", repo.branch),
                    ("notes", repo.notes),
                ],
            ),
        )

    @app.command("remove")
    def repo_remove_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Repo ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            repo = remove_repo_entry(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            repo.to_dict(),
            human=f"removed repo {repo.name}",
        )

    @app.command("set-role")
    def repo_set_role_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Repo ref.")],
        role: Annotated[
            str,
            typer.Option("--role", help="Repo role: read, write, or both."),
        ],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            repo = set_repo_role_entry(state.cwd, ref, role=role)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            repo.to_dict(),
            human=f"updated repo {repo.name} role={repo.role}",
        )

    @app.command("set-default")
    def repo_set_default_command(
        ctx: typer.Context,
        ref: Annotated[str, typer.Argument(..., help="Repo ref.")],
    ) -> None:
        state = cli_state_from_context(ctx)
        try:
            repo = set_default_execution_repo_entry(state.cwd, ref)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            repo.to_dict(),
            human=f"default execution repo set to {repo.name}",
        )

    @app.command("clear-default")
    def repo_clear_default_command(ctx: typer.Context) -> None:
        state = cli_state_from_context(ctx)
        try:
            clear_default_execution_repo_entry(state.cwd)
            repos = list_repos(state.cwd)
        except LaunchError as exc:
            emit_error(ctx, str(exc))
            raise typer.Exit(code=1) from exc
        emit_payload(
            ctx,
            [repo.to_dict() for repo in repos],
            human="cleared default execution repo",
        )
