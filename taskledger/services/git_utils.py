from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from taskledger.errors import LaunchError


@dataclass(slots=True, frozen=True)
class WorkspaceSnapshot:
    git_commit: str | None = None
    dirty: bool | None = None
    diff_hash: str | None = None
    status_hash: str | None = None
    captured_at: str | None = None


def capture_workspace_snapshot(workspace_root: Path) -> WorkspaceSnapshot:
    """Best-effort capture of the current workspace git state."""
    import hashlib

    from taskledger.timeutils import utc_now_iso

    root = git_root(workspace_root)
    if root is None:
        return WorkspaceSnapshot(captured_at=utc_now_iso())

    commit_result = run_git(root, "rev-parse", "HEAD", check=False)
    git_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None

    status_result = run_git(root, "status", "--porcelain=v1", check=False)
    status_text = status_result.stdout if status_result.returncode == 0 else ""
    dirty = bool(status_text.strip())
    status_hash = (
        "sha256:" + hashlib.sha256(status_text.encode()).hexdigest()
        if status_text.strip()
        else None
    )

    diff_result = run_git(root, "diff", "--binary", check=False)
    diff_text = diff_result.stdout if diff_result.returncode == 0 else ""
    diff_hash = (
        "sha256:" + hashlib.sha256(diff_text.encode()).hexdigest()
        if diff_text.strip()
        else None
    )

    return WorkspaceSnapshot(
        git_commit=git_commit,
        dirty=dirty,
        diff_hash=diff_hash,
        status_hash=status_hash,
        captured_at=utc_now_iso(),
    )


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
