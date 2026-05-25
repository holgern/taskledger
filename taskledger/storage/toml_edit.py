from __future__ import annotations

from collections.abc import Sequence


def is_toml_key_line(line: str, key: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith(key):
        return False
    rest = stripped[len(key) :]
    if not rest:
        return False
    rest = rest.lstrip()
    return rest.startswith("=")


def join_toml_lines(lines: Sequence[str]) -> str:
    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"
    return result
