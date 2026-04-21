from pathlib import Path

from taskledger.models import ContextSource, ContextBundle, ProjectSourceBudget
from taskledger.compose import (
    build_project_compose_payload,
    _compose_source_summary,
    _compose_warnings,
    _compose_input_counts,
    _compose_explanations,
    _relative_or_absolute,
)


def test_compose_source_summary_and_warnings():
    cs1 = ContextSource(
        kind="file",
        ref="f1",
        title="File One",
        body="content",
        metadata={"repo": "repo1"},
    )
    cs2 = ContextSource(
        kind="memory",
        ref="m1",
        title=None,
        body="body",
        metadata={"truncation_notice": "truncated", "repo": "repo1"},
    )
    cs3 = ContextSource(
        kind="file",
        ref="f2",
        title="File Two",
        body="content",
        metadata={"repo": "repo2", "truncation_notice": "notice"},
    )

    summary = _compose_source_summary((cs1, cs2, cs3))
    assert summary["total"] == 3
    assert summary["by_kind"] == {"file": 2, "memory": 1}
    assert summary["by_repo"] == {"repo1": 2, "repo2": 1}

    warnings = _compose_warnings((cs1, cs2, cs3))
    assert warnings == ("m1: truncated", "File Two: notice")


def test_compose_input_counts_and_explanations():
    explicit_inputs = {
        "memory_inputs": ("mem1",),
        "file_inputs": ("file1",),
        "item_inputs": (),
        "inline_inputs": (),
        "loop_artifact_inputs": (),
    }
    expanded_inputs = {
        "context_inputs": ("ctx1",),
        "memory_inputs": ("mem1",),
        "file_inputs": ("file1", "file2"),
        "item_inputs": (),
        "inline_inputs": (),
        "loop_artifact_inputs": (),
    }
    expansion_order = ["a", "b", "c", "d"]
    warnings_list = ["w1"]

    explanations = _compose_explanations(
        explicit_inputs=explicit_inputs,
        expanded_inputs=expanded_inputs,
        expansion_order=expansion_order,
        warnings=warnings_list,
    )

    # Expect the different explanation branches to be present
    assert any("saved contexts expanded into" in e for e in explanations)
    assert any("expanded file inputs include files pulled in" in e for e in explanations)
    assert any("expansion order shows additional source material" in e for e in explanations)
    assert any("truncation warnings explain" in e for e in explanations)

    counts = _compose_input_counts(expanded_inputs)
    assert counts["contexts"] == 1
    assert counts["memories"] == 1
    assert counts["files"] == 2
    assert counts["items"] == 0
    assert counts["inline"] == 0
    assert counts["loop_artifacts"] == 0


def test_relative_or_absolute(tmp_path: Path):
    workspace_root = tmp_path
    sub = workspace_root / "subdir"
    sub.mkdir()
    inside = sub / "file.txt"
    inside.write_text("x")

    outside = tmp_path.parent / "other.txt"
    outside.write_text("y")

    rel = _relative_or_absolute(inside, workspace_root)
    assert rel == str(Path("subdir") / "file.txt")

    abs_path = _relative_or_absolute(outside, workspace_root)
    assert abs_path == str(outside)


def test_build_project_compose_payload(tmp_path: Path):
    ws = tmp_path
    prompt_path = ws / "prompt.txt"
    prompt_path.write_text("prompt")

    cs = ContextSource(
        kind="file",
        ref="r1",
        title="T",
        body="b",
        metadata={"repo": "repo1", "truncation_notice": "tr"},
    )
    bundle = ContextBundle(name="b", sources=(cs,), composed_text="composed", content_hash="hash1")

    explicit_inputs = {
        "context_inputs": (),
        "memory_inputs": (),
        "file_inputs": (),
        "item_inputs": (),
        "inline_inputs": (),
        "loop_artifact_inputs": (),
    }
    expanded_inputs = {
        "context_inputs": ("ctx",),
        "memory_inputs": (),
        "file_inputs": ("f1",),
        "item_inputs": (),
        "inline_inputs": (),
        "loop_artifact_inputs": (),
    }
    details = {"expansion_order": ["f1"], "duplicates_removed": []}
    repo_refs = ("repo1",)
    execution_cwd = ws / "cwd"
    execution_cwd.mkdir()

    payload = build_project_compose_payload(
        workspace_root=ws,
        bundle=bundle,
        explicit_inputs=explicit_inputs,
        expanded_inputs=expanded_inputs,
        details=details,
        repo_refs=repo_refs,
        run_in_repo=None,
        run_in_repo_source=None,
        context_repo_refs=(),
        execution_cwd=execution_cwd,
        prompt_path=prompt_path,
        source_budget=ProjectSourceBudget(),
        prompt_diagnostics={"exceeds_hard_prompt_limit": True},
        user_prompt="u",
    )

    assert payload["kind"] == "project_compose"
    proj = payload["project"]
    assert proj["context_hash"] == "hash1"
    assert proj["repo_refs"] == ["repo1"]
    assert proj["execution_cwd"] == str(execution_cwd.relative_to(ws))
    assert "Composed prompt exceeds the local project safety limit before execution." in proj["warnings"]
    assert proj["prompt_path"] == str(prompt_path.relative_to(ws))
    assert proj["total_prompt_chars"] == len(bundle.composed_text)
    assert isinstance(proj["sources"], list)
    assert proj["sources"][0]["ref"] == "r1"
    # explanations are present in why
    assert isinstance(proj["why"]["explanations"], list)
