from __future__ import annotations

from pathlib import Path

from taskledger.api.composition import (
    SelectionRequest,
    build_compose_payload,
    build_sources,
    compose_bundle,
    expand_selection,
    repo_refs_for_sources,
)
from taskledger.api.contexts import save_context
from taskledger.api.items import create_item, write_item_memory_body
from taskledger.api.memories import create_memory
from taskledger.api.project import init_project
from taskledger.api.types import ContextSource, SourceBudget


def test_expand_selection_build_sources_and_compose_payload(tmp_path: Path) -> None:
    init_project(tmp_path)
    memory = create_memory(tmp_path, name="Plan Notes", body="alpha\nbeta\ngamma")
    save_context(
        tmp_path,
        name="Planning Context",
        memory_refs=(memory.id,),
        inline_texts=("inline note",),
    )

    request = SelectionRequest(context_names=("planning-context",))
    expanded = expand_selection(tmp_path, request)

    assert expanded.context_inputs == ("planning-context",)
    assert memory.id in expanded.memory_inputs
    assert "inline note" in expanded.inline_inputs

    sources = build_sources(
        tmp_path,
        expanded,
        source_budget=SourceBudget(max_source_chars=5),
    )

    assert sources
    assert any(source.truncated for source in sources)

    bundle = compose_bundle("Implement the work", sources)
    assert bundle.prompt == "Implement the work"
    assert "# User Task" in bundle.composed_text

    explicit_inputs = {
        "context_inputs": expanded.context_inputs,
        "memory_inputs": request.memory_refs,
        "file_inputs": request.file_refs,
        "item_inputs": request.item_refs,
        "inline_inputs": request.inline_texts,
        "loop_artifact_inputs": request.loop_latest_refs,
    }
    payload = build_compose_payload(
        context_name="planning-context",
        prompt=bundle.prompt,
        explicit_inputs=explicit_inputs,
        selected_repo_refs=repo_refs_for_sources(sources),
        run_in_repo=None,
        source_budget=SourceBudget(max_source_chars=5),
        bundle=bundle,
    )

    assert payload["kind"] == "project_compose"
    project = payload["project"]
    assert project["context_name"] == "planning-context"
    assert project["prompt"] == "Implement the work"
    assert project["memory_inputs"] == []
    assert project["context_inputs"] == ["planning-context"]
    assert project["sources"]


def test_repo_refs_for_sources_prefers_explicit_repo_refs() -> None:
    sources = (
        ContextSource(
            kind="file",
            ref="repo:file.py",
            title="file.py",
            repo_ref="core",
            text="print('x')",
            metadata=None,
        ),
        ContextSource(
            kind="file",
            ref="repo:file2.py",
            title="file2.py",
            repo_ref=None,
            text="print('y')",
            metadata={"repo": "addons"},
        ),
    )

    assert repo_refs_for_sources(sources) == ("core", "addons")


def test_build_sources_can_skip_item_memory_expansion(tmp_path: Path) -> None:
    init_project(tmp_path)
    item = create_item(tmp_path, slug="compose-item", description="Compose test item")
    write_item_memory_body(
        tmp_path,
        item.id,
        "plan",
        "Plan body",
    )

    request = SelectionRequest(item_refs=(item.id,), include_item_memories=False)
    selection = expand_selection(tmp_path, request)
    sources = build_sources(
        tmp_path,
        selection,
        include_item_memories=request.include_item_memories,
    )

    assert any(source.kind == "item" for source in sources)
    assert not any(
        source.kind == "memory"
        and source.metadata is not None
        and source.metadata.get("from_item") == item.id
        for source in sources
    )
