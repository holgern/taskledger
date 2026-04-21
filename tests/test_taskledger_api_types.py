from __future__ import annotations

from taskledger.api import types as api_types
from taskledger.models import ContextSource as ModelContextSource
from taskledger.models import ProjectSourceBudget


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
