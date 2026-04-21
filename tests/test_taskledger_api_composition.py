from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

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
from taskledger.api.repos import register_repo
from taskledger.api.types import ContextSource, SourceBudget
from taskledger.errors import LaunchError
from taskledger.storage import load_project_state, resolve_work_item, update_work_item


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


def test_build_sources_reference_mode_renders_file_and_directory_refs(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    source_file = tests_dir / "test_file.py"
    source_file.write_text("SECRET-CONTENT\n", encoding="utf-8")

    request = SelectionRequest(
        file_refs=("tests/test_file.py",),
        directory_refs=("tests",),
        file_render_mode="reference",
    )
    selection = expand_selection(tmp_path, request)
    sources = build_sources(tmp_path, selection)
    bundle = compose_bundle(prompt="Fix tests", sources=sources)

    assert any(source.text == "@tests/test_file.py" for source in sources)
    assert any(source.text == "@tests/" for source in sources)
    assert all("SECRET-CONTENT" not in source.text for source in sources)
    assert "## Directory Ref: tests/" in bundle.composed_text
    assert "@tests/test_file.py" in bundle.composed_text
    assert "@tests/" in bundle.composed_text


def test_build_sources_content_mode_rejects_directory_refs(tmp_path: Path) -> None:
    init_project(tmp_path)
    (tmp_path / "tests").mkdir()

    request = SelectionRequest(
        directory_refs=("tests",),
        file_render_mode="content",
    )
    selection = expand_selection(tmp_path, request)

    with pytest.raises(LaunchError, match="Directory refs require"):
        build_sources(tmp_path, selection)


def test_build_sources_reference_mode_applies_to_item_discovered_file_refs(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    discovered_file = tests_dir / "test_discovered.py"
    discovered_file.write_text("DISCOVERED-FILE-BODY\n", encoding="utf-8")
    item = create_item(tmp_path, slug="compose-discovered", description="desc")

    paths = load_project_state(tmp_path).paths
    current = resolve_work_item(paths, item.id)
    update_work_item(
        paths,
        item.id,
        replace(current, discovered_file_refs=("tests/test_discovered.py",)),
    )

    request = SelectionRequest(
        item_refs=(item.id,),
        include_item_memories=False,
        file_render_mode="reference",
    )
    selection = expand_selection(tmp_path, request)
    sources = build_sources(
        tmp_path,
        selection,
        include_item_memories=False,
    )
    discovered_sources = [
        source
        for source in sources
        if source.kind == "file"
        and source.metadata is not None
        and source.metadata.get("from_item") == item.id
    ]

    assert discovered_sources
    assert discovered_sources[0].text == "@tests/test_discovered.py"
    assert "DISCOVERED-FILE-BODY" not in discovered_sources[0].text


def test_build_sources_handles_non_utf8_by_mode(tmp_path: Path) -> None:
    init_project(tmp_path)
    bad_file = tmp_path / "binary.dat"
    bad_file.write_bytes(b"\xff\xfe\x00\x01")

    content_request = SelectionRequest(
        file_refs=("binary.dat",),
        file_render_mode="content",
    )
    content_selection = expand_selection(tmp_path, content_request)
    with pytest.raises(LaunchError, match="Failed to decode"):
        build_sources(tmp_path, content_selection)

    reference_request = SelectionRequest(
        file_refs=("binary.dat",),
        file_render_mode="reference",
    )
    reference_selection = expand_selection(tmp_path, reference_request)
    reference_sources = build_sources(tmp_path, reference_selection)

    assert any(source.text == "@binary.dat" for source in reference_sources)


def test_build_sources_rejects_outside_workspace_absolute_paths(tmp_path: Path) -> None:
    init_project(tmp_path)
    outside_file = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside_file.write_text("outside\n", encoding="utf-8")

    request = SelectionRequest(file_refs=(str(outside_file),))
    selection = expand_selection(tmp_path, request)
    with pytest.raises(LaunchError, match="outside workspace and registered repos"):
        build_sources(tmp_path, selection)


def test_build_sources_rejects_repo_path_traversal(tmp_path: Path) -> None:
    init_project(tmp_path)
    repo_dir = tmp_path / "core"
    repo_dir.mkdir()

    register_repo(tmp_path, name="Core", path=repo_dir, kind="generic", role="both")

    request = SelectionRequest(file_refs=("core:../../secret.txt",))
    selection = expand_selection(tmp_path, request)
    with pytest.raises(LaunchError, match="Invalid project repo file ref"):
        build_sources(tmp_path, selection)
