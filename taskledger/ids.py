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


def slugify_project_ref(value: str, *, empty: str = "item") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or empty
