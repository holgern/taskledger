from __future__ import annotations

from pathlib import Path

from ledgercore.errors import FrontMatterError
from ledgercore.frontmatter import (
    iter_markdown_files as _iter_markdown_files,
)
from ledgercore.frontmatter import (
    read_front_matter_document,
    write_front_matter_document,
)
from ledgercore.io import normalize_newlines

from taskledger.errors import LaunchError

MARKDOWN_FILE_VERSION = "v1"


def read_markdown_front_matter(path: Path) -> tuple[dict[str, object], str]:
    try:
        return read_front_matter_document(path)
    except FrontMatterError as exc:
        raise LaunchError(f"Invalid front matter document {path}: {exc}") from exc


def write_markdown_front_matter(
    path: Path,
    metadata: dict[str, object],
    body: str,
) -> None:
    try:
        write_front_matter_document(
            path,
            metadata,
            normalize_front_matter_newlines(body),
            body_mode="preserve",
            atomic=True,
        )
    except FrontMatterError as exc:
        raise LaunchError(f"Invalid front matter document {path}: {exc}") from exc


def iter_markdown_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return _iter_markdown_files(directory, recursive=False)


def normalize_front_matter_newlines(text: str) -> str:
    return normalize_newlines(text)
