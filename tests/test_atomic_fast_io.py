from __future__ import annotations

from pathlib import Path

from taskledger.storage import atomic


def test_atomic_write_skips_fsync_when_fast_test_io_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setenv("TASKLEDGER_TEST_FAST_IO", "1")
    monkeypatch.setattr(atomic.os, "fsync", lambda fd: calls.append(fd))

    atomic.atomic_write_text(tmp_path / "x.txt", "hello")

    assert (tmp_path / "x.txt").read_text(encoding="utf-8") == "hello"
    assert calls == []


def test_atomic_write_uses_fsync_by_default(tmp_path: Path, monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.delenv("TASKLEDGER_TEST_FAST_IO", raising=False)
    monkeypatch.setattr(atomic.os, "fsync", lambda fd: calls.append(fd))

    atomic.atomic_write_text(tmp_path / "x.txt", "hello")

    assert (tmp_path / "x.txt").read_text(encoding="utf-8") == "hello"
    assert calls
