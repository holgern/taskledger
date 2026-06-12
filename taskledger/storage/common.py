from __future__ import annotations

from pathlib import Path

from ledgercore.errors import JsonStoreError
from ledgercore.io import (
    content_hash as _content_hash,
)
from ledgercore.io import (
    merge_text as _merge_text,
)
from ledgercore.io import (
    read_text as _read_text,
)
from ledgercore.io import (
    write_text as _write_text,
)
from ledgercore.jsonio import (
    load_json_array as _load_json_array,
)
from ledgercore.jsonio import (
    load_json_object as _load_json_object,
)
from ledgercore.jsonio import (
    write_json as _write_json,
)

from taskledger.errors import LaunchError
from taskledger.storage.paths import ProjectPaths


def load_json_array(path: Path, label: str) -> list[dict[str, object]]:
    try:
        data = _load_json_array(path, label=label, missing="empty", empty="empty")
    except JsonStoreError as exc:
        message = str(exc)
        if "must contain a JSON array" in message:
            message = "expected a JSON array."
        raise LaunchError(f"Invalid {label} {path}: {message}") from exc
    return [item for item in data if isinstance(item, dict)]


def load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        return _load_json_object(path, label=label, missing="error", empty="empty")
    except JsonStoreError as exc:
        message = str(exc)
        if "must contain a JSON object" in message:
            message = "expected a JSON object."
        raise LaunchError(f"Invalid {label} {path}: {message}") from exc


def write_json(path: Path, payload: object) -> None:
    try:
        _write_json(path, payload, atomic=True)
    except JsonStoreError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc


def write_text(path: Path, contents: str) -> None:
    try:
        _write_text(path, contents, normalize=False)
    except OSError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc


def read_text(path: Path) -> str:
    try:
        return _read_text(path, normalize=False)
    except OSError as exc:
        raise LaunchError(f"Failed to read {path}: {exc}") from exc


def relative_to_project(paths: ProjectPaths, target: Path) -> str:
    return target.relative_to(paths.project_dir).as_posix()


def relative_to_workspace(paths: ProjectPaths, target: Path) -> str:
    try:
        return target.relative_to(paths.workspace_root).as_posix()
    except ValueError:
        return target.as_posix()


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
    return _content_hash(text)


def merge_text(current: str, incoming: str, *, prepend: bool) -> str:
    return _merge_text(current, incoming, prepend=prepend)
