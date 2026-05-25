from __future__ import annotations

import subprocess
from pathlib import Path

from taskledger.errors import LaunchError


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", root.as_posix(), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise LaunchError(
            f"git {' '.join(args)} failed in {root.as_posix()}: "
            f"{stderr or f'exit {result.returncode}'}"
        )
    return result


def git_root(path: Path) -> Path | None:
    candidate = path if path.exists() else path.parent
    result = subprocess.run(
        ["git", "-C", candidate.as_posix(), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def status_path_token(line: str) -> str:
    token = line[3:].strip()
    if "->" in token:
        token = token.split("->", 1)[1].strip()
    return token.strip('"')


def relative_to_git_root(path: Path, git_root_path: Path) -> str:
    try:
        return path.resolve().relative_to(git_root_path.resolve()).as_posix() or "."
    except ValueError as exc:
        raise LaunchError(
            f"{path.as_posix()} is not inside Git root {git_root_path.as_posix()}."
        ) from exc


def render_relative_or_absolute(workspace_root: Path, target: Path) -> str:
    try:
        return target.relative_to(workspace_root).as_posix()
    except ValueError:
        return target.as_posix()
