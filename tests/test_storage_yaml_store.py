"""Tests for taskledger.storage.yaml_store."""

from __future__ import annotations

from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.storage.yaml_store import load_yaml_object, write_yaml_object


@pytest.fixture()
def yaml_dir(tmp_path: Path) -> Path:
    return tmp_path / "yaml"
    # write_yaml_object creates parents, so no mkdir needed here


class TestLoadYamlObject:
    def test_missing_file_error_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.yaml"
        with pytest.raises(LaunchError, match="missing.yaml"):
            load_yaml_object(path, "test doc", missing="error")

    def test_missing_file_empty_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.yaml"
        result = load_yaml_object(path, "test doc", missing="empty")
        assert result == {}

    def test_empty_file_empty_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.yaml"
        path.write_text("", encoding="utf-8")
        result = load_yaml_object(path, "test doc", empty="empty")
        assert result == {}

    def test_valid_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "valid.yaml"
        path.write_text("key: value\n", encoding="utf-8")
        result = load_yaml_object(path, "test doc")
        assert result == {"key": "value"}

    def test_non_mapping_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "list.yaml"
        path.write_text("- item\n", encoding="utf-8")
        with pytest.raises(LaunchError, match="list.yaml"):
            load_yaml_object(path, "test doc")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text(":\n  :\n    {\n", encoding="utf-8")
        with pytest.raises(LaunchError, match="bad.yaml"):
            load_yaml_object(path, "test doc")


class TestWriteYamlObject:
    def test_writes_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "out.yaml"
        write_yaml_object(path, {"key": "value"})
        content = path.read_text(encoding="utf-8")
        assert "key: value" in content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "dir" / "out.yaml"
        write_yaml_object(path, {"key": "value"})
        assert path.exists()

    def test_deterministic_output(self, tmp_path: Path) -> None:
        path = tmp_path / "det.yaml"
        payload = {"b": 2, "a": 1}
        write_yaml_object(path, payload)
        first = path.read_text(encoding="utf-8")
        write_yaml_object(path, payload)
        second = path.read_text(encoding="utf-8")
        assert first == second

    def test_final_newline(self, tmp_path: Path) -> None:
        path = tmp_path / "nl.yaml"
        write_yaml_object(path, {"key": "value"})
        content = path.read_text(encoding="utf-8")
        assert content.endswith("\n")

    def test_write_then_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "roundtrip.yaml"
        payload = {"name": "test", "count": 42, "nested": {"x": 1}}
        write_yaml_object(path, payload)
        loaded = load_yaml_object(path, "roundtrip doc")
        assert loaded == payload
