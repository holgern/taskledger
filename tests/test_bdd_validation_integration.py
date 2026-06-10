# ruff: noqa: E501
"""Tests for BDD validation integration.

These tests exercise the real validation persistence path. They use a task
with an accepted plan whose acceptance criteria include ``ac-0001`` so that
``validate import-bdd-report`` actually creates durable validation checks
(Finding 3): the earlier version used a task with no accepted plan, so
persistence was silently swallowed and the tests proved nothing.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from taskledger.cli import app
from taskledger.storage.task_store import list_runs, load_bdd_reports
from tests.support.builders import create_implemented_task, init_workspace

runner = CliRunner()

AC_PLAN = """---
goal: Test goal.
acceptance_criteria:
  - id: ac-0001
    text: Criterion passes.
    mandatory: true
todos:
  - id: todo-0001
    text: Implement it.
    validation_hint: pytest tests
---

# Plan

Test plan.
"""


def _setup_implemented_task_with_validation(tmp_path) -> str:
    """Create a task with an accepted plan (ac-0001) and start validation."""
    init_workspace(tmp_path)
    task_id = create_implemented_task(tmp_path, plan_text=AC_PLAN)
    runner.invoke(app, ["validate", "start"])
    return task_id


def _write_cucumber_report(
    tmp_path, scenario_name: str, step_status: str, error_message: str = ""
) -> str:
    report = [
        {
            "name": "Test feature",
            "elements": [
                {
                    "type": "scenario",
                    "name": scenario_name,
                    "steps": [
                        {
                            "name": "step",
                            "result": {
                                "status": step_status,
                                "error_message": error_message,
                            },
                        },
                    ],
                }
            ],
        }
    ]
    report_path = tmp_path / "cucumber.json"
    report_path.write_text(json.dumps(report))
    return str(report_path)


def _write_junit_report(tmp_path, status: str = "passed") -> str:
    failure_block = (
        '      <failure message="AssertionError">Expected X but got Y</failure>\n'
        if status == "failed"
        else ""
    )
    report_path = tmp_path / "junit.xml"
    report_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<testsuites>\n"
        '  <testsuite name="BDD Tests" tests="1" failures="0">\n'
        '    <testcase classname="tests.test_task_management_plan_gates" '
        'file="tests/test_task_management_plan_gates.py" '
        'name="test_agent_cannot_start_implementation_before_plan_approval">\n'
        f"{failure_block}"
        "    </testcase>\n"
        "  </testsuite>\n"
        "</testsuites>\n",
        encoding="utf-8",
    )
    return str(report_path)


def _write_behavior_assets(tmp_path) -> tuple[str, str]:
    feature_rel = "specs/behavior/features/task-management/plan-gates.feature"
    feature_path = tmp_path / feature_rel
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    feature_path.write_text("Feature: Plan gates\n", encoding="utf-8")
    pytest_rel = "tests/test_task_management_plan_gates.py"
    pytest_path = tmp_path / pytest_rel
    pytest_path.parent.mkdir(parents=True, exist_ok=True)
    pytest_path.write_text(
        "def test_agent_cannot_start_implementation_before_plan_approval():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    pytest_ref = (
        "tests/test_task_management_plan_gates.py::"
        "test_agent_cannot_start_implementation_before_plan_approval"
    )
    return feature_rel, pytest_ref


class TestBddValidationIntegration:
    # specweave: feature=specs/behavior/features/bdd_validation_integration/bdd-validation-integration.feature
    # specweave: scenario=@bdd-bdd-validation-integration-import-bdd-report-creates-validation-checks
    def test_import_bdd_report_creates_validation_checks(
        self, tmp_path, monkeypatch
    ) -> None:
        """Import BDD report should persist validation checks for linked criteria."""
        monkeypatch.chdir(tmp_path)
        _setup_implemented_task_with_validation(tmp_path)

        # Create BDD structure linked to ac-0001.
        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test passes",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )
        feature_file, pytest_ref = _write_behavior_assets(tmp_path)
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "link-automation",
                "bdd-0001",
                "--feature-file",
                feature_file,
                "--scenario",
                "@bdd-implementation-blocked-before-plan-acceptance",
                "--pytest",
                pytest_ref,
            ],
        )

        report_path = _write_junit_report(tmp_path, "passed")

        # Import report.
        result = runner.invoke(
            app,
            [
                "--json",
                "validate",
                "import-bdd-report",
                report_path,
                "--format",
                "junit-xml",
                "--command",
                (
                    "pytest tests/test_task_management_plan_gates.py "
                    "--junitxml=reports/behavior/task-management-plan-gates-junit.xml"
                ),
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert "bdd-0001" in payload["result"]["matched_examples"]
        assert payload["result"]["result"] == "passed"

        # Finding 3: assert a real validation check was persisted.
        checks = payload["result"]["validation_checks"]
        assert len(checks) == 1
        assert checks[0]["check_id"] == "check-0001"
        assert checks[0]["criterion_id"] == "ac-0001"
        assert checks[0]["status"] == "pass"
        assert checks[0]["example_id"] == "bdd-0001"

        # The BDD report record carries the persisted check ref.
        reports = load_bdd_reports(tmp_path, "task-0001")
        assert reports[0].validation_check_refs == ("check-0001",)

        # The validation run actually contains the BDD check.
        validation_run = list_runs(tmp_path, "task-0001")[-1]
        assert validation_run.run_type == "validation"
        bdd_check = validation_run.checks[-1]
        assert bdd_check.id == "check-0001"
        assert bdd_check.criterion_id == "ac-0001"
        assert bdd_check.status == "pass"
        # Finding 4: rich evidence (scenario/command/report path) is preserved.
        evidence_blob = " ".join(bdd_check.evidence)
        assert (
            "scenario: @bdd-implementation-blocked-before-plan-acceptance"
            in evidence_blob
        )
        assert (
            "command: pytest tests/test_task_management_plan_gates.py" in evidence_blob
        )
        assert "pytest_file: tests/test_task_management_plan_gates.py" in evidence_blob
        assert f"pytest_nodeid: {pytest_ref}" in evidence_blob
        assert "report:" in evidence_blob

    # specweave: feature=specs/behavior/features/bdd_validation_integration/bdd-validation-integration.feature
    # specweave: scenario=@bdd-bdd-validation-integration-failing-bdd-report-blocks-validation-finish
    def test_failing_bdd_report_blocks_validation_finish(
        self, tmp_path, monkeypatch
    ) -> None:
        """A failing BDD check must block validate finish --result passed."""
        monkeypatch.chdir(tmp_path)
        _setup_implemented_task_with_validation(tmp_path)

        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test fails",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )

        report_path = _write_cucumber_report(
            tmp_path, "Test fails", "failed", "Expected X"
        )

        # Import failing report and confirm the failing check is persisted.
        import_result = runner.invoke(
            app,
            [
                "--json",
                "validate",
                "import-bdd-report",
                report_path,
                "--format",
                "cucumber-json",
            ],
        )
        assert import_result.exit_code == 0
        checks = json.loads(import_result.stdout)["result"]["validation_checks"]
        assert len(checks) == 1
        assert checks[0]["status"] == "fail"
        assert checks[0]["check_id"] == "check-0001"

        # Finishing validation as passed must fail because ac-0001 is failing.
        finish_result = runner.invoke(
            app,
            ["validate", "finish", "--result", "passed", "--summary", "All good"],
        )
        assert finish_result.exit_code != 0

    # specweave: feature=specs/behavior/features/bdd_validation_integration/bdd-validation-integration.feature
    # specweave: scenario=@bdd-bdd-validation-integration-import-bdd-report-without-active-validation-fails-clearly
    def test_import_bdd_report_without_active_validation_fails_clearly(
        self, tmp_path, monkeypatch
    ) -> None:
        """Linked criteria without an active validation run must fail (Finding 2)."""
        monkeypatch.chdir(tmp_path)
        init_workspace(tmp_path)
        # Task with an accepted plan (ac-0001) but NO validation run started.
        create_implemented_task(tmp_path, plan_text=AC_PLAN)

        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test passes",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )

        report_path = _write_cucumber_report(tmp_path, "Test passes", "passed")

        result = runner.invoke(
            app,
            [
                "--json",
                "validate",
                "import-bdd-report",
                report_path,
                "--format",
                "cucumber-json",
            ],
        )
        # Finding 2: no silent swallow; the command fails with a clear message.
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert "persistence failed" in payload["error"]["message"]

    # specweave: feature=specs/behavior/features/bdd_validation_integration/bdd-validation-integration.feature
    # specweave: scenario=@bdd-bdd-validation-integration-import-bdd-report-without-accepted-plan-fails-clearly
    def test_import_bdd_report_without_accepted_plan_fails_clearly(
        self, tmp_path, monkeypatch
    ) -> None:
        """Linked criteria without an accepted plan must fail (Finding 2)."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["task", "create", "Test task"])
        runner.invoke(app, ["task", "activate", "task-0001"])
        runner.invoke(app, ["implement", "start"])
        runner.invoke(app, ["implement", "finish", "--summary", "Done"])
        runner.invoke(app, ["validate", "start"])

        runner.invoke(app, ["bdd", "init", "--feature", "Test feature"])
        runner.invoke(
            app,
            [
                "bdd",
                "example",
                "add",
                "--title",
                "Test passes",
                "--given",
                "a",
                "--when",
                "b",
                "--then",
                "c",
                "--acceptance-criterion",
                "ac-0001",
            ],
        )

        report_path = _write_cucumber_report(tmp_path, "Test passes", "passed")

        result = runner.invoke(
            app,
            [
                "--json",
                "validate",
                "import-bdd-report",
                report_path,
                "--format",
                "cucumber-json",
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert "persistence failed" in payload["error"]["message"]
