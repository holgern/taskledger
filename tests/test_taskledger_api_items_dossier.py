from __future__ import annotations

from pathlib import Path

from taskledger.api.contexts import save_context
from taskledger.api.items import (
    create_item,
    item_dossier,
    item_knowledge,
    render_item_dossier_markdown,
    write_item_memory_body,
)
from taskledger.api.project import init_project
from taskledger.api.validation import append_validation_record


def _section_by_title(dossier, title: str):
    return next(
        (section for section in dossier.sections if section.title == title),
        None,
    )


def test_item_dossier_default_sections_include_memory_bodies(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="dossier-core", description="Inspect item text")
    write_item_memory_body(tmp_path, item.id, "plan", "Plan section text")
    write_item_memory_body(tmp_path, item.id, "implementation", "Implementation text")

    dossier = item_dossier(
        tmp_path,
        item.id,
        include_runs=False,
        include_validation=False,
        include_workflow=False,
        include_contexts=False,
    )

    plan = _section_by_title(dossier, "Plan")
    implementation = _section_by_title(dossier, "Implementation")
    assert plan is not None
    assert implementation is not None
    assert "Plan section text" in plan.body
    assert "Implementation text" in implementation.body

    rendered = render_item_dossier_markdown(dossier)
    assert "ITEM DOSSIER dossier-core (it-1)" in rendered
    assert "Plan section text" in rendered


def test_item_dossier_respects_role_filter_and_include_empty(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="dossier-filter", description="Role filtering")
    write_item_memory_body(tmp_path, item.id, "plan", "Only plan text")

    filtered = item_dossier(
        tmp_path,
        item.id,
        roles=("plan",),
        include_runs=False,
        include_validation=False,
        include_workflow=False,
        include_contexts=False,
    )
    assert _section_by_title(filtered, "Plan") is not None
    assert _section_by_title(filtered, "Analysis") is None

    with_empty = item_dossier(
        tmp_path,
        item.id,
        roles=("analysis",),
        include_empty=True,
        include_runs=False,
        include_validation=False,
        include_workflow=False,
        include_contexts=False,
    )
    analysis = _section_by_title(with_empty, "Analysis")
    assert analysis is not None
    assert analysis.body == "(empty)"

    without_empty = item_dossier(
        tmp_path,
        item.id,
        roles=("analysis",),
        include_empty=False,
        include_runs=False,
        include_validation=False,
        include_workflow=False,
        include_contexts=False,
    )
    assert _section_by_title(without_empty, "Analysis") is None


def test_item_dossier_includes_validation_and_referencing_contexts(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="dossier-links", description="Linked sections")
    write_item_memory_body(tmp_path, item.id, "validation", "Validation summary")
    append_validation_record(
        tmp_path,
        project_item_ref=item.id,
        memory_ref=item.validation_memory_ref or "mem-2",
        kind="smoke",
        status="passed",
    )
    save_context(tmp_path, name="Review Context", item_refs=(item.id,))

    dossier = item_dossier(
        tmp_path,
        item.id,
        include_runs=False,
        include_workflow=False,
        include_validation=True,
        include_contexts=True,
    )

    validation = _section_by_title(dossier, "Related Validation Records")
    contexts = _section_by_title(dossier, "Contexts Referencing This Item")
    assert validation is not None
    assert contexts is not None
    assert "val-1" in validation.body
    assert "Review Context (ctx-1)" in contexts.body


def test_item_knowledge_highlights_missing_evidence_and_commands(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="knowledge-gap", description="Knowledge gaps")

    payload = item_knowledge(tmp_path, item.id)

    assert payload["approval_ready"] is False
    assert payload["blocking_requirements"] == [
        "plan content",
        "acceptance criteria",
        "validation checklist",
    ]
    assert payload["plan_memory"]["status"] == "missing"
    assert payload["commands"] == [
        'taskledger item memory write knowledge-gap --role plan --text "..."',
        'taskledger item update knowledge-gap --add-acceptance "..."',
        'taskledger item update knowledge-gap --add-validation-check "..."',
    ]


def test_item_knowledge_points_to_approve_when_plan_exists(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="knowledge-ready", description="Ready item")
    write_item_memory_body(tmp_path, item.id, "plan", "Plan content")

    payload = item_knowledge(tmp_path, item.id)

    assert payload["approval_ready"] is True
    assert payload["blocking_requirements"] == []
    assert payload["plan_memory"]["status"] == "present"
    assert payload["plan_memory"]["command"] == (
        "taskledger item memory show knowledge-ready --role plan"
    )
    assert payload["commands"] == ["taskledger item approve knowledge-ready"]
