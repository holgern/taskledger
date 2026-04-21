from __future__ import annotations

from pathlib import Path

from taskledger.api.project import init_project
from taskledger.api.repos import register_repo
from taskledger.api.runs import show_run
from taskledger.api.runtime_support import (
    create_run_artifact_layout,
    get_effective_project_config,
    resolve_repo_root,
    save_run_record,
)
from taskledger.api.types import ProjectConfig, RunRecord


def test_get_effective_project_config_applies_overrides(tmp_path: Path) -> None:
    init_project(tmp_path)
    config_path = tmp_path / ".taskledger" / "project.toml"
    config_path.write_text(
        'default_memory_update_mode = "append"\n',
        encoding="utf-8",
    )

    merged = get_effective_project_config(tmp_path)
    assert merged.default_memory_update_mode == "append"

    base = ProjectConfig(default_save_run_reports=False)
    merged_from_base = get_effective_project_config(tmp_path, base_config=base)
    assert merged_from_base.default_save_run_reports is False


def test_create_run_artifact_layout_and_save_run_record(tmp_path: Path) -> None:
    init_project(tmp_path)

    layout = create_run_artifact_layout(tmp_path, origin="runtime")
    run_dir = Path(layout.run_dir)
    assert run_dir.exists()
    assert Path(layout.metadata_file) == run_dir / "record.json"

    run_id = run_dir.name
    record = _run_record(run_id)
    saved = save_run_record(tmp_path, record)

    assert saved.run_id == run_id
    loaded = show_run(tmp_path, run_id)
    assert loaded.run_id == run_id
    assert loaded.status == "succeeded"


def test_resolve_repo_root_via_runtime_support(tmp_path: Path) -> None:
    init_project(tmp_path)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    register_repo(
        tmp_path,
        name="Main Repo",
        path=repo_dir,
        kind="generic",
        role="both",
    )

    resolved = resolve_repo_root(tmp_path, "main-repo")
    assert resolved == repo_dir.resolve()


def _run_record(run_id: str) -> RunRecord:
    base = f".taskledger/runs/{run_id}"
    return RunRecord(
        run_id=run_id,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        memory_inputs=(),
        file_inputs=(),
        item_inputs=(),
        inline_inputs=(),
        context_inputs=(),
        loop_artifact_inputs=(),
        save_target=None,
        save_mode=None,
        stage=None,
        repo_refs=(),
        context_hash="hash",
        status="succeeded",
        result_path=f"{base}/result.json",
        preview_path=f"{base}/preview.json",
        prompt_path=f"{base}/prompt.txt",
        composed_prompt_path=f"{base}/composed_prompt.txt",
        report_path=None,
    )
