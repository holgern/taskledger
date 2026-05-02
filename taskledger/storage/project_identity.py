"""Stable project identity for cross-machine export/import safety.

The ``project_uuid`` is stored in the checked-in taskledger TOML file
(``.taskledger.toml`` / ``taskledger.toml``) and is independent of
``ledger_ref``.  It identifies the *source project*, not a branch ledger.
"""

from __future__ import annotations

import importlib
import uuid as _uuid
from pathlib import Path

from taskledger.errors import LaunchError
from taskledger.storage.atomic import atomic_write_text

try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    tomllib = importlib.import_module("tomli")

PROJECT_UUID_KEY = "project_uuid"


def new_project_uuid() -> str:
    """Return a fresh canonical UUID4 string."""
    return str(_uuid.uuid4())


def normalize_project_uuid(value: object) -> str:
    """Validate and return a canonical lowercase project UUID string.

    Raises ``LaunchError`` on invalid input.
    """
    if not isinstance(value, str):
        raise LaunchError(
            f"project_uuid must be a string, got {type(value).__name__!r}."
        )
    try:
        parsed = _uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise LaunchError(f"Invalid project_uuid {value!r}: {exc}") from exc
    return str(parsed)


def load_project_uuid(config_path: Path) -> str | None:
    """Read ``project_uuid`` from ``config_path``, or return ``None`` if absent."""
    if not config_path.exists():
        return None
    data = _load_toml(config_path)
    raw = data.get(PROJECT_UUID_KEY)
    if raw is None:
        return None
    return normalize_project_uuid(raw)


def ensure_project_uuid(config_path: Path) -> str:
    """Return the existing project UUID or generate, persist, and return a new one.

    This is the primary backfill entrypoint: it reads the config TOML,
    returns the UUID if present, and otherwise atomically appends one.
    """
    existing = load_project_uuid(config_path)
    if existing is not None:
        return existing

    value = new_project_uuid()
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updated = insert_or_append_project_uuid(text, value)
    atomic_write_text(config_path, updated)
    return value


def assert_same_project_uuid(expected: str, actual: str) -> None:
    """Raise ``LaunchError`` when two project UUIDs differ."""
    if expected != actual:
        raise LaunchError(
            f"Project UUID mismatch. Refusing to import taskledger archive.\n"
            f"archive: {expected}\n"
            f"local:   {actual}"
        )


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def insert_or_append_project_uuid(text: str, value: str) -> str:
    """Insert ``project_uuid = "..."`` into TOML text, preserving comments.

    Placement rules:

    * After the ``taskledger_dir = ...`` line if one exists.
    * Otherwise appended before the ledger block, or at end of file.
    * Preserves trailing newline.
    """
    lines = text.split("\n") if text else []

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("taskledger_dir") and _is_toml_key_line(
            stripped, "taskledger_dir"
        ):
            new_lines = list(lines)
            new_lines.insert(idx + 1, "")
            new_lines.insert(
                idx + 2,
                "# Stable project identity. Commit this with your source tree.",
            )
            new_lines.insert(idx + 3, f'project_uuid = "{value}"')
            return _join_lines(new_lines)

    # No taskledger_dir line – try before the ledger block.
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("ledger_ref") and _is_toml_key_line(
            stripped, "ledger_ref"
        ):
            new_lines = list(lines)
            new_lines.insert(idx, "")
            new_lines.insert(
                idx + 1, "# Stable project identity. Commit with your source tree."
            )
            new_lines.insert(idx + 2, f'project_uuid = "{value}"')
            return _join_lines(new_lines)

    # Fallback: append at the end.
    if lines and lines[-1].strip():
        lines.append("")
    lines.append("# Stable project identity. Commit this with your source tree.")
    lines.append(f'project_uuid = "{value}"')
    return _join_lines(lines)


def _load_toml(path: Path) -> dict[object, object]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    result = tomllib.loads(text)
    if not isinstance(result, dict):
        raise LaunchError(f"Invalid project config {path}: expected a TOML table.")
    return result


def _is_toml_key_line(stripped: str, key: str) -> bool:
    if not stripped.startswith(key):
        return False
    rest = stripped[len(key) :]
    if not rest:
        return False
    rest = rest.lstrip()
    return rest.startswith("=")


def _join_lines(lines: list[str]) -> str:
    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"
    return result
