from __future__ import annotations

import re
from pathlib import Path

import yaml

from taskledger.errors import LaunchError
from taskledger.storage.common import read_text as _read_text
from taskledger.storage.common import write_text as _write_text

_FRONT_MATTER_PATTERN = re.compile(r"^---\n(?P<meta>.*?)\n---(?:\n|$)", re.DOTALL)


def read_markdown_front_matter(path: Path) -> tuple[dict[str, object], str]:
    text = normalize_front_matter_newlines(_read_text(path))
    match = _FRONT_MATTER_PATTERN.match(text)
    if match is None:
        raise LaunchError(
            f"Invalid front matter document {path}: expected leading YAML front matter."
        )
    metadata_text = match.group("meta")
    try:
        raw_metadata = yaml.safe_load(metadata_text)
    except yaml.YAMLError as exc:
        raise LaunchError(f"Invalid YAML front matter in {path}: {exc}") from exc
    if raw_metadata is None:
        metadata: dict[str, object] = {}
    elif isinstance(raw_metadata, dict):
        metadata = raw_metadata
    else:
        raise LaunchError(
            f"Invalid YAML front matter in {path}: expected a mapping."
        )
    body = text[match.end() :]
    return metadata, body


def write_markdown_front_matter(
    path: Path,
    metadata: dict[str, object],
    body: str,
) -> None:
    normalized_body = normalize_front_matter_newlines(body)
    yaml_text = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
    yaml_text = normalize_front_matter_newlines(yaml_text)
    contents = f"---\n{yaml_text}---\n{normalized_body}"
    _write_text(path, contents)


def iter_markdown_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path for path in directory.glob("*.md") if path.is_file()
    )


def normalize_front_matter_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
