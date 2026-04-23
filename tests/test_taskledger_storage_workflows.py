from __future__ import annotations

import json
from pathlib import Path

import pytest

from taskledger.errors import LaunchError
from taskledger.models import ProjectPaths
from taskledger.storage.workflows import (
    delete_workflow_definition,
    load_workflow_definitions,
    resolve_workflow_definition,
    save_workflow_definitions,
)


def _make_paths(tmp_path: Path) -> ProjectPaths:
    return ProjectPaths(
        workspace_root=tmp_path,
        project_dir=tmp_path / ".taskledger",
        config_path=tmp_path / ".taskledger" / "project.toml",
        repos_dir=tmp_path / ".taskledger" / "repos",
        repo_index_path=tmp_path / ".taskledger" / "repos" / "index.json",
        workflows_dir=tmp_path / ".taskledger" / "workflows",
        workflow_index_path=tmp_path / ".taskledger" / "workflows" / "index.json",
        memories_dir=tmp_path / ".taskledger" / "memories",
        memory_index_path=tmp_path / ".taskledger" / "memories" / "index.json",
        contexts_dir=tmp_path / ".taskledger" / "contexts",
        context_index_path=tmp_path / ".taskledger" / "contexts" / "index.json",
        items_dir=tmp_path / ".taskledger" / "items",
        item_index_path=tmp_path / ".taskledger" / "items" / "index.json",
        stages_dir=tmp_path / ".taskledger" / "stages",
        stage_index_path=tmp_path / ".taskledger" / "stages" / "index.json",
        runs_dir=tmp_path / ".taskledger" / "runs",
    )


def _workflow_dict(workflow_id: str = "wf-1") -> dict[str, object]:
    return {
        "workflow_id": workflow_id,
        "name": "Test workflow",
        "version": "1",
        "default_for_items": False,
        "stages": [
            {
                "stage_id": "intake",
                "label": "Intake",
                "kind": "human",
                "order": 0,
                "requires_approval_before_entry": False,
                "allows_human_completion": True,
                "allows_runtime_execution": False,
                "output_kind": None,
                "save_target_rule": None,
                "validation_rule": None,
                "instruction_template_id": None,
            }
        ],
        "transitions": [
            {
                "from_stage": None,
                "to_stage": "intake",
                "rule": "create",
                "condition": None,
            }
        ],
    }


def _write_index(paths: ProjectPaths, items: list[dict[str, object]]) -> None:
    paths.workflow_index_path.parent.mkdir(parents=True, exist_ok=True)
    paths.workflow_index_path.write_text(
        json.dumps(items, indent=2), encoding="utf-8"
    )


class TestLoadWorkflowDefinitions:
    def test_returns_empty_when_index_missing(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        assert load_workflow_definitions(paths) == []

    def test_returns_parsed_workflows(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        _write_index(paths, [_workflow_dict("wf-a"), _workflow_dict("wf-b")])

        result = load_workflow_definitions(paths)
        assert len(result) == 2
        assert result[0].workflow_id == "wf-a"
        assert result[1].workflow_id == "wf-b"


class TestSaveWorkflowDefinitions:
    def test_round_trip(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        _write_index(paths, [_workflow_dict("wf-1")])

        loaded = load_workflow_definitions(paths)
        loaded[0] = loaded[0]  # use as-is
        save_workflow_definitions(paths, loaded)

        reloaded = load_workflow_definitions(paths)
        assert len(reloaded) == 1
        assert reloaded[0].workflow_id == "wf-1"


class TestResolveWorkflowDefinition:
    def test_finds_existing_workflow(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        _write_index(paths, [_workflow_dict("wf-target")])

        result = resolve_workflow_definition(paths, "wf-target")
        assert result.workflow_id == "wf-target"

    def test_raises_for_unknown_workflow(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        _write_index(paths, [_workflow_dict("wf-other")])

        with pytest.raises(LaunchError, match="Unknown workflow definition"):
            resolve_workflow_definition(paths, "wf-missing")


class TestDeleteWorkflowDefinition:
    def test_removes_workflow_and_returns_it(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        _write_index(
            paths, [_workflow_dict("wf-keep"), _workflow_dict("wf-delete")]
        )

        deleted = delete_workflow_definition(paths, "wf-delete")
        assert deleted.workflow_id == "wf-delete"

        remaining = load_workflow_definitions(paths)
        assert len(remaining) == 1
        assert remaining[0].workflow_id == "wf-keep"

    def test_raises_for_unknown_workflow(self, tmp_path: Path) -> None:
        paths = _make_paths(tmp_path)
        _write_index(paths, [_workflow_dict("wf-only")])

        with pytest.raises(LaunchError, match="Unknown workflow definition"):
            delete_workflow_definition(paths, "wf-missing")
