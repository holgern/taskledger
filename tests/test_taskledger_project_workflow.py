from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from taskledger.api.contexts import save_context
from taskledger.api.items import create_item
from taskledger.api.memories import write_memory_body
from taskledger.api.project import (
    init_project,
    project_doctor,
    project_next,
    project_report,
)
from taskledger.api.runtime_support import get_effective_project_config
from taskledger.storage import load_project_state, update_work_item


def test_get_effective_project_config_reads_workflow_metadata(tmp_path: Path) -> None:
    init_project(tmp_path)
    _write_workflow_config(tmp_path / ".taskledger" / "project.toml")

    config = get_effective_project_config(tmp_path)

    assert config.workflow_schema == "opsx-lite"
    assert config.project_context == "Prioritize dependencies before execution."
    assert config.default_artifact_order == ("analysis", "plan", "implementation")
    assert [rule.name for rule in config.artifact_rules] == [
        "analysis",
        "plan",
        "implementation",
    ]
    assert config.artifact_rules[1].depends_on == ("analysis",)


def test_project_next_and_report_use_workflow_dependencies(tmp_path: Path) -> None:
    init_project(tmp_path)
    _write_workflow_config(tmp_path / ".taskledger" / "project.toml")

    blocked = create_item(tmp_path, slug="blocked", description="Blocked item")
    ready = create_item(tmp_path, slug="ready", description="Ready item")

    state = load_project_state(tmp_path, recent_runs_limit=None)
    blocked_item = next(item for item in state.work_items if item.id == blocked.id)
    update_work_item(
        state.paths,
        blocked.id,
        replace(blocked_item, depends_on=(ready.id,)),
    )
    write_memory_body(tmp_path, ready.analysis_memory_ref or "", "analysis complete")

    next_step = project_next(tmp_path)
    report = project_report(tmp_path)

    assert next_step is not None
    assert next_step["item_ref"] == ready.id
    assert next_step["workflow_artifact"] == "plan"
    assert next_step["workflow_schema"] == "opsx-lite"
    assert report["status"]["workflow"]["counts"]["ready"] == 1
    assert report["status"]["workflow"]["counts"]["blocked"] == 1
    assert report["doctor"]["workflow"]["blocked_items"] == [blocked.id]
    assert "Workflow dependencies block some items." in report["doctor"]["warnings"]


def test_project_doctor_reports_broken_loop_refs_and_missing_item_dependencies(
    tmp_path: Path,
) -> None:
    init_project(tmp_path)
    create_item(tmp_path, slug="doctor-case", description="Doctor case")
    save_context(
        tmp_path,
        name="Broken Loop",
        loop_latest_refs=("missing/loop-output.txt",),
    )

    state = load_project_state(tmp_path, recent_runs_limit=None)
    item = state.work_items[0]
    update_work_item(
        state.paths,
        item.id,
        replace(item, depends_on=("item-9999",)),
    )

    payload = project_doctor(tmp_path)

    assert payload["healthy"] is False
    assert payload["broken_context_refs"] == [
        "broken-loop: artifacts=missing/loop-output.txt"
    ]
    assert payload["broken_item_links"] == ["item-0001: depends_on=item-9999"]


def _write_workflow_config(path: Path) -> None:
    path.write_text(
        """
workflow_schema = "opsx-lite"
project_context = "Prioritize dependencies before execution."
default_artifact_order = ["analysis", "plan", "implementation"]

[artifact_rules.analysis]
label = "Analysis"
memory_ref_field = "analysis_memory_ref"

[artifact_rules.plan]
depends_on = ["analysis"]
memory_ref_field = "plan_memory_ref"

[artifact_rules.implementation]
depends_on = ["plan"]
memory_ref_field = "implementation_memory_ref"
""".strip()
        + "\n",
        encoding="utf-8",
    )
