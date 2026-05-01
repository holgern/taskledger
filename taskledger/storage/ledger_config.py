"""Ledger config parsing, validation, and atomic update for branch-scoped state."""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from taskledger.errors import LaunchError

try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    tomllib = importlib.import_module("tomli")

LEDGER_REF_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
LEDGER_REF_MAX_LENGTH = 80

LEDGER_CONFIG_KEYS = frozenset(
    {
        "ledger_ref",
        "ledger_parent_ref",
        "ledger_next_task_number",
        "ledger_branch_guard",
    }
)


@dataclass(slots=True, frozen=True)
class LedgerConfig:
    ref: str = "main"
    parent_ref: str | None = None
    next_task_number: int = 1
    branch_guard: Literal["off", "warn", "error"] = "off"


@dataclass(slots=True, frozen=True)
class LedgerConfigPatch:
    """Partial update to apply to ledger config keys in .taskledger.toml."""

    ref: str | None = None
    parent_ref: str | None = None
    next_task_number: int | None = None
    branch_guard: Literal["off", "warn", "error"] | None = None


def validate_ledger_ref(value: str) -> str:
    """Validate and normalise a ledger ref string.

    Returns the validated string.
    Raises LaunchError on invalid input.
    """
    if not value:
        raise LaunchError("ledger_ref must be a non-empty string.")
    if len(value) > LEDGER_REF_MAX_LENGTH:
        raise LaunchError(
            f"ledger_ref must be at most {LEDGER_REF_MAX_LENGTH} characters."
        )
    if not LEDGER_REF_PATTERN.match(value):
        raise LaunchError("ledger_ref may only contain a-z, A-Z, 0-9, '.', '_', '-'.")
    if ".." in value:
        raise LaunchError("ledger_ref must not contain '..'.")
    if "/" in value or "\\" in value:
        raise LaunchError("ledger_ref must not contain path separators.")
    return value


def load_ledger_config(config_path: Path) -> LedgerConfig:
    """Load LedgerConfig from a .taskledger.toml file.

    If ledger keys are absent, returns sensible defaults (ref="main").
    """
    if not config_path.exists():
        return LedgerConfig()
    try:
        text = config_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise LaunchError(f"Failed to read {config_path}: {exc}") from exc
    if not text:
        return LedgerConfig()
    try:
        data = tomllib.loads(text)
    except Exception as exc:  # pragma: no cover
        raise LaunchError(f"Invalid project config {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LaunchError(
            f"Invalid project config {config_path}: expected a TOML table."
        )
    return _ledger_config_from_dict(data)


def _ledger_config_from_dict(data: dict[object, object]) -> LedgerConfig:
    ref = data.get("ledger_ref")
    if ref is not None:
        if not isinstance(ref, str):
            raise LaunchError("ledger_ref must be a string.")
        validate_ledger_ref(ref)
    else:
        ref = "main"

    parent_ref = data.get("ledger_parent_ref")
    if parent_ref is not None:
        if not isinstance(parent_ref, str):
            raise LaunchError("ledger_parent_ref must be a string.")
        parent_ref = parent_ref or None
    else:
        parent_ref = None

    next_task_number = data.get("ledger_next_task_number")
    if next_task_number is not None:
        if not isinstance(next_task_number, int) or next_task_number < 1:
            raise LaunchError("ledger_next_task_number must be a positive integer.")
    else:
        next_task_number = 1

    branch_guard = data.get("ledger_branch_guard")
    if branch_guard is not None:
        if branch_guard not in ("off", "warn", "error"):
            raise LaunchError("ledger_branch_guard must be one of: off, warn, error.")
    else:
        branch_guard = "off"

    return LedgerConfig(
        ref=ref,
        parent_ref=parent_ref,
        next_task_number=next_task_number,
        branch_guard=branch_guard,  # type: ignore[arg-type]
    )


def update_ledger_config(config_path: Path, patch: LedgerConfigPatch) -> LedgerConfig:
    """Atomically update ledger keys in .taskledger.toml.

    Preserves comments and non-ledger keys. Writes only the four ledger keys.
    """
    current_text = ""
    if config_path.exists():
        try:
            current_text = config_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise LaunchError(f"Failed to read {config_path}: {exc}") from exc

    # Validate patch values before writing
    if patch.ref is not None:
        validate_ledger_ref(patch.ref)
    if patch.next_task_number is not None and patch.next_task_number < 1:
        raise LaunchError("ledger_next_task_number must be a positive integer.")
    if patch.branch_guard is not None and patch.branch_guard not in (
        "off",
        "warn",
        "error",
    ):
        raise LaunchError("ledger_branch_guard must be one of: off, warn, error.")

    # Build the replacement values
    current_config = _ledger_config_from_dict(
        tomllib.loads(current_text) if current_text else {}
    )
    new_ref = patch.ref if patch.ref is not None else current_config.ref
    new_parent_ref = (
        patch.parent_ref
        if patch.parent_ref is not None
        else (current_config.parent_ref or "")
    )
    new_next = (
        patch.next_task_number
        if patch.next_task_number is not None
        else current_config.next_task_number
    )
    new_guard = (
        patch.branch_guard
        if patch.branch_guard is not None
        else current_config.branch_guard
    )

    updated_text = _apply_ledger_patch(
        current_text,
        ref=new_ref,
        parent_ref=new_parent_ref,
        next_task_number=new_next,
        branch_guard=new_guard,
    )

    from taskledger.storage.atomic import atomic_write_text

    atomic_write_text(config_path, updated_text)

    return LedgerConfig(
        ref=new_ref,
        parent_ref=new_parent_ref or None,
        next_task_number=new_next,
        branch_guard=new_guard,
    )


def _apply_ledger_patch(
    text: str,
    *,
    ref: str,
    parent_ref: str,
    next_task_number: int,
    branch_guard: str,
) -> str:
    """Rewrite ledger keys in TOML text, preserving everything else."""
    lines = text.split("\n") if text else []

    keys_to_set = {
        "ledger_ref": ref,
        "ledger_parent_ref": parent_ref,
        "ledger_next_task_number": str(next_task_number),
        "ledger_branch_guard": branch_guard,
    }
    toml_value_map = {
        "ledger_ref": lambda v: f'"{v}"',
        "ledger_parent_ref": lambda v: f'"{v}"',
        "ledger_next_task_number": lambda v: v,
        "ledger_branch_guard": lambda v: f'"{v}"',
    }

    found_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Check if this line is a top-level key = value assignment
        matched_key = None
        for key in keys_to_set:
            if stripped.startswith(key) and _is_toml_key_line(stripped, key):
                matched_key = key
                break

        if matched_key is not None:
            value = keys_to_set[matched_key]
            formatted = toml_value_map[matched_key](value)
            new_lines.append(f"{matched_key} = {formatted}")
            found_keys.add(matched_key)
        else:
            new_lines.append(line)

    # Append missing keys
    missing = set(keys_to_set.keys()) - found_keys
    if missing:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(
            "# Taskledger branch-scoped state."
            " This block is intentionally safe to commit."
        )
        for key in (
            "ledger_ref",
            "ledger_parent_ref",
            "ledger_next_task_number",
            "ledger_branch_guard",
        ):
            if key in missing:
                value = keys_to_set[key]
                formatted = toml_value_map[key](value)
                new_lines.append(f"{key} = {formatted}")

    result = "\n".join(new_lines)
    # Ensure trailing newline
    if result and not result.endswith("\n"):
        result += "\n"
    return result


def _is_toml_key_line(stripped: str, key: str) -> bool:
    """Check if a stripped line is 'key = ...' (not inside a table or array)."""
    if not stripped.startswith(key):
        return False
    rest = stripped[len(key) :]
    # Must be followed by optional whitespace then '='
    if not rest:
        return False
    rest = rest.lstrip()
    return rest.startswith("=")
