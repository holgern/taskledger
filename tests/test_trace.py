from __future__ import annotations

import json

from typer.testing import CliRunner

from taskledger.api.bdd import (
    bdd_example_add,
    bdd_example_link_archledger,
    bdd_example_link_automation,
    bdd_init,
)
from taskledger.cli import app
from taskledger.domain.models import FileLink, LinkCollection
from taskledger.services.bdd_reports import import_bdd_report
from taskledger.services.trace import build_task_trace
from taskledger.storage.task_store import save_links
from tests.support.builders import create_implemented_task, init_workspace

runner = CliRunner()


def test_trace_task_without_bdd_reports_gap(tmp_path) -> None:
    init_workspace(tmp_path)
    task_id = create_implemented_task(tmp_path)

    payload = build_task_trace(tmp_path, task_id)

    assert payload["schema"] == "combi.trace.v1"
    assert payload["producer"] == "taskledger"
    assert payload["subject"] == {"type": "task", "id": task_id}
    assert payload["task_ids"] == [task_id]
    assert payload["ac_ids"] == ["ac-0001"]
    assert payload["bdd_ids"] == []
    assert payload["gaps"][0]["kind"] == "missing_behavior_mapping"


def test_trace_includes_bdd_mapping_validation_evidence_and_archledger_refs(
    tmp_path,
) -> None:
    init_workspace(tmp_path)
    task_id = create_implemented_task(tmp_path)
    bdd_init(tmp_path, task_id, "Trace feature")
    bdd_example_add(
        tmp_path,
        task_id,
        title="Scenario passes",
        given=("a task",),
        when=("evidence is imported",),
        then=("trace links it",),
        acceptance_criteria=("ac-0001",),
    )
    bdd_example_link_archledger(tmp_path, task_id, "bdd-0001", "al_runtime_0123")
    bdd_example_link_automation(
        tmp_path,
        task_id,
        "bdd-0001",
        feature_file="specs/behavior/features/task-management/trace.feature",
        scenario="@bdd-0001",
        pytest_ref="tests/test_task_management_trace.py::test_trace",
        allow_missing=True,
    )
    report_path = tmp_path / "report.xml"
    report_path.write_text(
        '<testsuite name="s"><testcase classname="test_task_management_trace" '
        'name="test_trace" file="tests/test_task_management_trace.py" /></testsuite>'
    )
    import_bdd_report(tmp_path, task_id, str(report_path), "junit-xml", "pytest")
    save_links(
        tmp_path,
        LinkCollection(
            task_id=task_id,
            links=(
                FileLink(
                    path="adr-0042",
                    kind="other",
                    target_type="architecture-decision",
                ),
            ),
        ),
    )

    payload = build_task_trace(tmp_path, task_id)

    assert payload["bdd_ids"] == ["bdd-0001"]
    assert "al_runtime_0123" in payload["archledger_refs"]
    assert "adr-0042" in payload["archledger_refs"]
    assert (
        "specs/behavior/features/task-management/trace.feature"
        in payload["source_refs"]
    )
    assert "tests/test_task_management_trace.py::test_trace" in payload["test_refs"]
    assert "bdd-report-0001" in payload["evidence_refs"]
    assert payload["gaps"] == []


def test_trace_cli_format_json_is_raw_json(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    init_workspace(tmp_path)
    task_id = create_implemented_task(tmp_path)

    result = runner.invoke(app, ["trace", task_id, "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema"] == "combi.trace.v1"
    assert payload["task_ids"] == [task_id]
