from __future__ import annotations

from taskledger.api import types as api_types
from taskledger.models import ContextSource as ModelContextSource
from taskledger.models import ExecutionRequest, ProjectContextEntry, ProjectSourceBudget


def test_types_module_exposes_short_canonical_names() -> None:
    assert api_types.WorkItem.__name__ == "ProjectWorkItem"
    assert api_types.Memory.__name__ == "ProjectMemory"
    assert api_types.ContextEntry.__name__ == "ProjectContextEntry"
    assert api_types.Repo.__name__ == "ProjectRepo"
    assert api_types.RunRecord.__name__ == "ProjectRunRecord"


def test_source_budget_round_trip_with_project_model() -> None:
    budget = api_types.SourceBudget(
        max_source_chars=100,
        max_total_chars=300,
        head_lines=10,
        tail_lines=5,
        line_start=2,
        line_end=8,
    )
    project_budget = budget.to_project_source_budget()

    assert project_budget == ProjectSourceBudget(
        max_source_chars=100,
        max_total_chars=300,
        head_lines=10,
        tail_lines=5,
        line_start=2,
        line_end=8,
    )
    assert api_types.SourceBudget.from_project_source_budget(project_budget) == budget


def test_context_source_conversion_preserves_metadata() -> None:
    model_source = ModelContextSource(
        kind="file",
        ref="repo:README.md",
        title="README",
        body="hello",
        metadata={"repo": "main", "truncated": True, "path": "/tmp/README.md"},
    )

    source = api_types.ContextSource.from_model(model_source)

    assert source.text == "hello"
    assert source.repo_ref == "main"
    assert source.truncated is True

    converted_back = source.to_model()
    assert converted_back.body == "hello"
    assert converted_back.metadata is not None
    assert converted_back.metadata["repo"] == "main"
    assert converted_back.metadata["truncated"] is True


def test_item_dossier_types_serialize_to_dict() -> None:
    section = api_types.ItemDossierSection(
        kind="memory_body",
        title="Plan",
        ref="mem-0001",
        body="Implement X",
        metadata={"role": "plan"},
    )
    dossier = api_types.ItemDossier(
        item_ref="item-0001",
        title="Improve coverage",
        sections=(section,),
        metadata={"selected_roles": ["plan"]},
    )

    assert section.to_dict()["title"] == "Plan"
    payload = dossier.to_dict()
    assert payload["item_ref"] == "item-0001"
    assert payload["sections"][0]["ref"] == "mem-0001"


def test_execution_request_round_trip_for_file_render_mode_and_directories() -> None:
    request = ExecutionRequest(
        request_id="req-0001",
        item_ref="item-0001",
        workflow_id="wf-1",
        stage_id="implement",
        file_inputs=("tests/test_a.py",),
        directory_inputs=("tests",),
        file_render_mode="reference",
    )

    payload = request.to_dict()
    reloaded = ExecutionRequest.from_dict(payload)

    assert payload["directory_inputs"] == ["tests"]
    assert payload["file_render_mode"] == "reference"
    assert reloaded.directory_inputs == ("tests",)
    assert reloaded.file_render_mode == "reference"


def test_execution_request_from_dict_defaults_new_fields() -> None:
    payload = {
        "request_id": "req-0001",
        "item_ref": "item-0001",
        "workflow_id": "wf-1",
        "stage_id": "implement",
    }

    reloaded = ExecutionRequest.from_dict(payload)

    assert reloaded.directory_inputs == ()
    assert reloaded.file_render_mode == "content"


def test_project_context_entry_from_dict_defaults_directory_refs() -> None:
    payload = {
        "name": "My Context",
        "slug": "my-context",
        "path": "contexts/my-context.json",
        "memory_refs": ["mem-0001"],
        "file_refs": ["tests/test_a.py"],
        "item_refs": ["item-0001"],
        "inline_texts": [],
        "loop_latest_refs": [],
        "summary": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:01Z",
    }

    entry = ProjectContextEntry.from_dict(payload)

    assert entry.directory_refs == ()
    assert entry.to_dict()["directory_refs"] == []
