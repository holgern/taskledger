from __future__ import annotations

import re


def next_project_id(prefix: str, existing_ids: list[str]) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    max_value = 0
    for item in existing_ids:
        match = pattern.match(item)
        if match is None:
            continue
        max_value = max(max_value, int(match.group(1)))
    return f"{prefix}-{max_value + 1:04d}"


def allocate_ledger_task_id(
    existing_ids: list[str],
    config_next_number: int,
) -> tuple[str, int]:
    """Allocate a ledger-scoped task ID.

    Returns (task_id, new_next_number) where new_next_number
    should be written back to .taskledger.toml.
    """
    pattern = re.compile(r"^task-(\d+)$")
    max_existing = 0
    for item in existing_ids:
        match = pattern.match(item)
        if match is None:
            continue
        max_existing = max(max_existing, int(match.group(1)))
    next_number = max(config_next_number, max_existing + 1)
    task_id = f"task-{next_number:04d}"
    return task_id, next_number + 1


def slugify_project_ref(value: str, *, empty: str = "item") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or empty
