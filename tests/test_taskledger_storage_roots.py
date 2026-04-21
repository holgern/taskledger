from __future__ import annotations

from pathlib import Path

from taskledger.storage import (
    ensure_project_exists,
    init_project_state,
    resolve_project_paths,
    resolve_taskledger_root,
)


def test_init_project_state_creates_taskledger_root(tmp_path: Path) -> None:
    paths, created = init_project_state(tmp_path)

    assert paths.project_dir == tmp_path / ".taskledger"
    assert paths.project_dir.exists()
    assert created


def test_resolve_project_paths_always_uses_taskledger_root(tmp_path: Path) -> None:
    legacy_root = _create_legacy_root(tmp_path)
    init_project_state(tmp_path)

    paths = resolve_project_paths(tmp_path)

    assert legacy_root.exists()
    assert paths.project_dir == resolve_taskledger_root(tmp_path)


def test_ensure_project_exists_ignores_legacy_root_when_taskledger_missing(
    tmp_path: Path,
) -> None:
    _create_legacy_root(tmp_path)

    try:
        ensure_project_exists(tmp_path)
    except Exception as exc:
        assert "Project state is not initialized" in str(exc)
    else:
        raise AssertionError("ensure_project_exists unexpectedly accepted legacy state")


def _create_legacy_root(workspace_root: Path) -> Path:
    legacy_root = workspace_root / ".runtildone" / "project"
    for directory in (
        legacy_root,
        legacy_root / "repos",
        legacy_root / "memories",
        legacy_root / "contexts",
        legacy_root / "pbis",
        legacy_root / "plans",
        legacy_root / "items",
        legacy_root / "runs",
        legacy_root / "validation",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for path in (
        legacy_root / "project.toml",
        legacy_root / "repos" / "index.json",
        legacy_root / "memories" / "index.json",
        legacy_root / "contexts" / "index.json",
        legacy_root / "pbis" / "index.json",
        legacy_root / "plans" / "plan.json",
        legacy_root / "items" / "index.json",
        legacy_root / "validation" / "records.json",
    ):
        path.write_text("" if path.suffix == ".toml" else "[]\n", encoding="utf-8")
    return legacy_root
