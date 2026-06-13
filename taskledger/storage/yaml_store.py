"""YAML I/O wrappers backed by ledgercore.yamlio.

All taskledger production YAML reads/writes should go through these
wrappers so that ledgercore exception types never leak into service
or CLI code.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from ledgercore.errors import YamlStoreError
from ledgercore.yamlio import load_yaml_object as _load_yaml_object
from ledgercore.yamlio import write_yaml as _write_yaml

from taskledger.errors import LaunchError


def load_yaml_object(
    path: Path,
    label: str,
    *,
    missing: Literal["error", "empty"] = "error",
    empty: Literal["error", "empty"] = "empty",
) -> dict[str, object]:
    try:
        return _load_yaml_object(path, label=label, missing=missing, empty=empty)
    except YamlStoreError as exc:
        raise LaunchError(f"Invalid {label} {path}: {exc}") from exc


def write_yaml_object(
    path: Path,
    payload: Mapping[str, object],
    *,
    sort_keys: bool = False,
) -> None:
    try:
        _write_yaml(path, payload, atomic=True, sort_keys=sort_keys)
    except YamlStoreError as exc:
        raise LaunchError(f"Failed to write {path}: {exc}") from exc
