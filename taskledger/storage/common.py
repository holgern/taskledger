from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.storage.paths import ProjectPaths


def load_json_array(path: Path, label: str) -> list[dict[str, object]]:
    if not path.exists():
        return []
    text = read_text(path).strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Invalid {label} {path}: {exc}") from exc
    if not isinstance(data, list):
        raise LaunchError(f"Invalid {label} {path}: expected a JSON array.")
    return [item for item in data if isinstance(item, dict)]


def load_json_object(path: Path, label: str) -> dict[str, object]:
    text = read_text(path).strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Invalid {label} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LaunchError(f"Invalid {label} {path}: expected a JSON object.")
    return data


def write_json(path: Path, payload: object) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, contents: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    except OSError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LaunchError(f"Failed to read {path}: {exc}") from exc


def relative_to_project(paths: ProjectPaths, target: Path) -> str:
    return str(target.relative_to(paths.project_dir))


def relative_to_workspace(paths: ProjectPaths, target: Path) -> str:
    try:
        return str(target.relative_to(paths.workspace_root))
    except ValueError:
        return str(target)


def summarize_text(text: str) -> str | None:
    stripped = " ".join(text.split())
    if not stripped:
        return None
    if len(stripped) <= 80:
        return stripped
    return stripped[:77] + "..."


def content_hash(text: str) -> str | None:
    if not text:
        return None
    return sha256(text.encode("utf-8")).hexdigest()


def merge_text(current: str, incoming: str, *, prepend: bool) -> str:
    if not current:
        return incoming
    if not incoming:
        return current
    combined = [incoming, current] if prepend else [current, incoming]
    return "\n\n".join(part.rstrip("\n") for part in combined if part)
