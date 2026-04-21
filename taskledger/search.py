from __future__ import annotations

import ast
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths, ProjectRepo
from taskledger.storage import load_repos, resolve_repo, resolve_repo_root

SearchMatchKind = Literal["path", "content", "symbol"]

_TEXT_EXTENSIONS = {
    ".csv",
    ".html",
    ".js",
    ".json",
    ".md",
    ".po",
    ".py",
    ".rst",
    ".scss",
    ".sql",
    ".toml",
    ".ts",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
_SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "__pycache__", "node_modules"}
_SYMBOL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "python",
        re.compile(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    ),
    (
        "javascript",
        re.compile(
            r"^\s*(?:function|class)\s+([A-Za-z_$][A-Za-z0-9_$]*)", re.MULTILINE
        ),
    ),
    ("xml-id", re.compile(r"""\bid=["']([^"']+)["']""")),
)


@dataclass(slots=True, frozen=True)
class ProjectSearchMatch:
    repo: str
    path: str
    kind: SearchMatchKind
    line: int | None
    text: str
    symbol: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "repo": self.repo,
            "path": self.path,
            "kind": self.kind,
            "line": self.line,
            "text": self.text,
            "symbol": self.symbol,
        }


@dataclass(slots=True, frozen=True)
class ProjectDependencyInfo:
    repo: str
    module: str
    manifest_path: str
    depends: tuple[str, ...]
    module_name: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "repo": self.repo,
            "module": self.module,
            "manifest_path": self.manifest_path,
            "depends": list(self.depends),
            "module_name": self.module_name,
        }


def search_project(
    paths: ProjectPaths,
    *,
    query: str,
    repo_refs: tuple[str, ...] = (),
    limit: int = 50,
) -> list[ProjectSearchMatch]:
    lowered_query = query.strip().lower()
    if not lowered_query:
        raise LaunchError("Project search query must not be empty.")
    matches: list[ProjectSearchMatch] = []
    for repo, file_path, relative_path in iter_repo_files(paths, repo_refs=repo_refs):
        path_text = relative_path.as_posix()
        if lowered_query in path_text.lower():
            matches.append(
                ProjectSearchMatch(
                    repo=repo.name,
                    path=path_text,
                    kind="path",
                    line=None,
                    text=path_text,
                )
            )
        if len(matches) >= limit:
            break
        content = _read_text_file(file_path)
        if content is None:
            continue
        content_matches = 0
        for index, line in enumerate(content.splitlines(), start=1):
            if lowered_query not in line.lower():
                continue
            matches.append(
                ProjectSearchMatch(
                    repo=repo.name,
                    path=path_text,
                    kind="content",
                    line=index,
                    text=line.strip(),
                )
            )
            content_matches += 1
            if len(matches) >= limit or content_matches >= 3:
                break
        if len(matches) >= limit:
            break
    return matches


def grep_project(
    paths: ProjectPaths,
    *,
    pattern: str,
    repo_refs: tuple[str, ...] = (),
    limit: int = 100,
) -> list[ProjectSearchMatch]:
    if not pattern.strip():
        raise LaunchError("Project grep pattern must not be empty.")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise LaunchError(f"Invalid project grep pattern: {exc}") from exc
    matches: list[ProjectSearchMatch] = []
    for repo, file_path, relative_path in iter_repo_files(paths, repo_refs=repo_refs):
        content = _read_text_file(file_path)
        if content is None:
            continue
        for index, line in enumerate(content.splitlines(), start=1):
            if compiled.search(line) is None:
                continue
            matches.append(
                ProjectSearchMatch(
                    repo=repo.name,
                    path=relative_path.as_posix(),
                    kind="content",
                    line=index,
                    text=line.strip(),
                )
            )
            if len(matches) >= limit:
                return matches
    return matches


def symbols_project(
    paths: ProjectPaths,
    *,
    query: str,
    repo_refs: tuple[str, ...] = (),
    limit: int = 50,
) -> list[ProjectSearchMatch]:
    lowered_query = query.strip().lower()
    if not lowered_query:
        raise LaunchError("Project symbol query must not be empty.")
    matches: list[ProjectSearchMatch] = []
    for repo, file_path, relative_path in iter_repo_files(paths, repo_refs=repo_refs):
        content = _read_text_file(file_path)
        if content is None:
            continue
        for _, pattern in _SYMBOL_PATTERNS:
            for match in pattern.finditer(content):
                symbol = match.group(1)
                if lowered_query not in symbol.lower():
                    continue
                line = content.count("\n", 0, match.start()) + 1
                matches.append(
                    ProjectSearchMatch(
                        repo=repo.name,
                        path=relative_path.as_posix(),
                        kind="symbol",
                        line=line,
                        text=symbol,
                        symbol=symbol,
                    )
                )
                if len(matches) >= limit:
                    return matches
    return matches


def module_dependencies(
    paths: ProjectPaths,
    *,
    repo_ref: str,
    module: str,
) -> ProjectDependencyInfo:
    repo = resolve_repo(paths, repo_ref)
    repo_root = resolve_repo_root(paths, repo.name)
    manifest_path = _find_module_manifest(repo_root, module)
    if manifest_path is None:
        raise LaunchError(f"Could not find module '{module}' in repo {repo.name}.")
    try:
        payload = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as exc:
        raise LaunchError(f"Failed to parse manifest {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LaunchError(f"Manifest {manifest_path} must contain a dict literal.")
    depends = payload.get("depends", [])
    if not isinstance(depends, list) or not all(
        isinstance(item, str) for item in depends
    ):
        raise LaunchError(f"Manifest {manifest_path} has an invalid depends list.")
    module_name = payload.get("name")
    if module_name is not None and not isinstance(module_name, str):
        raise LaunchError(f"Manifest {manifest_path} has an invalid module name.")
    return ProjectDependencyInfo(
        repo=repo.name,
        module=module,
        manifest_path=str(manifest_path.relative_to(repo_root)),
        depends=tuple(depends),
        module_name=module_name,
    )


def iter_repo_files(
    paths: ProjectPaths, *, repo_refs: tuple[str, ...] = ()
) -> Iterable[tuple[ProjectRepo, Path, Path]]:
    repos = _selected_repos(paths, repo_refs)
    for repo in repos:
        repo_root = resolve_repo_root(paths, repo.name)
        for root, dirnames, filenames in os.walk(repo_root):
            dirnames[:] = [
                item
                for item in dirnames
                if item not in _SKIP_DIRS and not item.startswith(".")
            ]
            for filename in filenames:
                file_path = Path(root) / filename
                if file_path.suffix and file_path.suffix not in _TEXT_EXTENSIONS:
                    continue
                yield repo, file_path, file_path.relative_to(repo_root)


def discover_relevant_files(
    paths: ProjectPaths,
    *,
    query: str,
    repo_refs: tuple[str, ...] = (),
    limit: int = 12,
) -> tuple[str, ...]:
    tokens = _discovery_tokens(query)
    if not tokens:
        raise LaunchError("Project discovery query must contain useful search terms.")
    scored: list[tuple[int, str]] = []
    for repo, file_path, relative_path in iter_repo_files(paths, repo_refs=repo_refs):
        path_text = relative_path.as_posix().lower()
        content = _read_text_file(file_path)
        lowered_content = content.lower() if content is not None else ""
        score = 0
        for token in tokens:
            if token in path_text:
                score += 4
            if lowered_content and token in lowered_content:
                score += 1
        if relative_path.name == "__manifest__.py":
            score += 1
        if score <= 0:
            continue
        scored.append((score, f"{repo.name}:{relative_path.as_posix()}"))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[1] for item in scored[:limit])


def _selected_repos(
    paths: ProjectPaths, repo_refs: tuple[str, ...]
) -> list[ProjectRepo]:
    if repo_refs:
        return [resolve_repo(paths, ref) for ref in repo_refs]
    repos = load_repos(paths)
    if not repos:
        raise LaunchError("No project repos are registered.")
    return repos


def _read_text_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError as exc:
        raise LaunchError(f"Failed to read {path}: {exc}") from exc


def _find_module_manifest(repo_root: Path, module: str) -> Path | None:
    for root, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            item
            for item in dirnames
            if item not in _SKIP_DIRS and not item.startswith(".")
        ]
        if "__manifest__.py" not in filenames:
            continue
        candidate = Path(root)
        if candidate.name == module:
            return candidate / "__manifest__.py"
    return None


def _discovery_tokens(query: str) -> tuple[str, ...]:
    stop_words = {
        "and",
        "for",
        "from",
        "have",
        "into",
        "that",
        "the",
        "this",
        "with",
    }
    tokens: list[str] = []
    for token in re.findall(r"[a-zA-Z0-9_]+", query.lower()):
        if len(token) < 4 or token in stop_words or token in tokens:
            continue
        tokens.append(token)
    return tuple(tokens[:16])
