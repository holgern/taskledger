"""Tests for BDD report import service."""

from __future__ import annotations

import json

import pytest

from taskledger.api.bdd import bdd_example_add, bdd_example_link_automation, bdd_init
from taskledger.errors import LaunchError
from taskledger.services.bdd_reports import import_bdd_report


class TestCucumberJsonImport:
    # sw: f=specs/behavior/features/bdd_report_import/bdd-report-import.feature
    # sw: s=@bdd-bdd-report-import-cucumber-results-preserve-pass-and-fail
    def test_import_passing_cucumber_report(self, tmp_path) -> None:
        """Test importing a passing Cucumber JSON report."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="Test passes",
            given=("something",),
            when=("action",),
            then=("result",),
            acceptance_criteria=("ac-0001",),
        )

        # Create Cucumber JSON report
        report = [
            {
                "name": "Test feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Test passes",
                        "steps": [
                            {"name": "something", "result": {"status": "passed"}},
                            {"name": "action", "result": {"status": "passed"}},
                            {"name": "result", "result": {"status": "passed"}},
                        ],
                    }
                ],
            }
        ]
        report_path = tmp_path / "cucumber.json"
        report_path.write_text(json.dumps(report))

        result = import_bdd_report(
            tmp_path, "task-0001", str(report_path), "cucumber-json", "pytest -q"
        )

        assert result["kind"] == "bdd_report_import"
        assert result["format"] == "cucumber-json"
        assert result["result"] == "passed"
        assert "bdd-0001" in result["matched_examples"]
        assert len(result["unmatched_scenarios"]) == 0
        assert len(result["validation_checks"]) == 1
        assert result["validation_checks"][0]["status"] == "pass"
        assert result["validation_checks"][0]["criterion_id"] == "ac-0001"

    def test_import_failing_cucumber_report(self, tmp_path) -> None:
        """Test importing a failing Cucumber JSON report."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="Test fails",
            given=("something",),
            when=("action",),
            then=("result",),
            acceptance_criteria=("ac-0001",),
        )

        report = [
            {
                "name": "Test feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Test fails",
                        "steps": [
                            {"name": "something", "result": {"status": "passed"}},
                            {
                                "name": "action",
                                "result": {
                                    "status": "failed",
                                    "error_message": "Expected X but got Y",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
        report_path = tmp_path / "cucumber.json"
        report_path.write_text(json.dumps(report))

        result = import_bdd_report(
            tmp_path, "task-0001", str(report_path), "cucumber-json"
        )

        assert result["result"] == "failed"
        assert result["result"] == "failed"
        assert result["validation_checks"][0]["status"] == "fail"

    @pytest.mark.parametrize(
        "step_status",
        ["skipped", "pending", "undefined", "ambiguous", "error", "unknown"],
    )
    def test_import_non_passed_cucumber_report_does_not_pass(
        self, tmp_path, step_status
    ) -> None:
        """Any non-`passed` Cucumber step must fail the scenario (Finding 1)."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="Flaky scenario",
            given=("something",),
            when=("action",),
            then=("result",),
            acceptance_criteria=("ac-0001",),
        )

        report = [
            {
                "name": "Test feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Flaky scenario",
                        "steps": [
                            {
                                "name": "action",
                                "result": {
                                    "status": step_status,
                                    "error_message": f"step was {step_status}",
                                },
                            },
                        ],
                    }
                ],
            }
        ]
        report_path = tmp_path / "cucumber.json"
        report_path.write_text(json.dumps(report))

        result = import_bdd_report(
            tmp_path, "task-0001", str(report_path), "cucumber-json"
        )

        assert result["result"] == "failed"
        assert result["validation_checks"][0]["status"] == "fail"
        assert result["validation_checks"][0]["criterion_id"] == "ac-0001"

    def test_import_unmatched_scenarios(self, tmp_path) -> None:
        """Test importing report with unmatched scenarios."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="Known scenario",
            given=("x",),
            when=("y",),
            then=("z",),
        )

        report = [
            {
                "name": "Test feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Unknown scenario",
                        "steps": [
                            {"name": "step", "result": {"status": "passed"}},
                        ],
                    }
                ],
            }
        ]
        report_path = tmp_path / "cucumber.json"
        report_path.write_text(json.dumps(report))

        result = import_bdd_report(
            tmp_path, "task-0001", str(report_path), "cucumber-json"
        )

        assert len(result["matched_examples"]) == 0
        assert "Unknown scenario" in result["unmatched_scenarios"]
        assert len(result["warnings"]) == 1
        # Finding 8 (additive): unmatched reporting is surfaced but does not
        # change overall result semantics.
        assert result["unmatched_count"] == 1
        assert result["has_unmatched_failures"] is False
        assert result["result"] == "unknown"  # no matched scenarios

        from taskledger.storage.task_store import load_bdd_reports

        reports = load_bdd_reports(tmp_path, "task-0001")
        assert reports[0].unmatched_count == 1
        assert reports[0].has_unmatched_failures is False

    # sw: f=specs/behavior/features/bdd_report_import/bdd-report-import.feature
    # sw: s=@bdd-bdd-report-import-unmatched-failures-are-visible
    def test_import_unmatched_failing_scenario_surfaces_flag(self, tmp_path) -> None:
        """An unmatched failing scenario sets has_unmatched_failures (Finding 8)."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="Known scenario",
            given=("x",),
            when=("y",),
            then=("z",),
            acceptance_criteria=("ac-0001",),
        )

        report = [
            {
                "name": "Test feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Known scenario",
                        "steps": [
                            {
                                "name": "step",
                                "result": {"status": "passed"},
                            },
                        ],
                    },
                    {
                        "type": "scenario",
                        "name": "Unknown failing scenario",
                        "steps": [
                            {
                                "name": "step",
                                "result": {
                                    "status": "failed",
                                    "error_message": "boom",
                                },
                            },
                        ],
                    },
                ],
            }
        ]
        report_path = tmp_path / "cucumber.json"
        report_path.write_text(json.dumps(report))

        result = import_bdd_report(
            tmp_path, "task-0001", str(report_path), "cucumber-json"
        )

        assert "Known scenario" in result["matched_examples"] or (
            "bdd-0001" in result["matched_examples"]
        )
        assert result["matched_examples"] == ["bdd-0001"]
        assert result["unmatched_count"] == 1
        assert result["has_unmatched_failures"] is True
        # Overall result stays scoped to matched scenarios (additive only).
        assert result["result"] == "passed"

    # sw: f=specs/behavior/features/bdd_report_import/bdd-report-import.feature
    # sw: s=@bdd-bdd-report-import-invalid-input-is-rejected
    def test_import_missing_file(self, tmp_path) -> None:
        """Test importing a missing report file."""
        with pytest.raises(LaunchError, match="Report file not found"):
            import_bdd_report(
                tmp_path, "task-0001", "nonexistent.json", "cucumber-json"
            )

    def test_import_unsupported_format(self, tmp_path) -> None:
        """Test importing with unsupported format."""
        report_path = tmp_path / "test.json"
        report_path.write_text("[]")
        with pytest.raises(LaunchError, match="Unsupported report format"):
            import_bdd_report(tmp_path, "task-0001", str(report_path), "unknown-format")

    def test_import_invalid_json(self, tmp_path) -> None:
        """Test importing invalid JSON."""
        report_path = tmp_path / "bad.json"
        report_path.write_text("not json {{{")
        with pytest.raises(LaunchError, match="Invalid Cucumber JSON"):
            import_bdd_report(tmp_path, "task-0001", str(report_path), "cucumber-json")


class TestJunitXmlImport:
    # sw: f=specs/behavior/features/bdd_report_import/bdd-report-import.feature
    # sw: s=@bdd-bdd-report-import-import-passing-junit-report
    def test_import_passing_junit_report(self, tmp_path) -> None:
        """Test importing a passing JUnit XML report."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="JUnit test passes",
            given=("something",),
            when=("action",),
            then=("result",),
            acceptance_criteria=("ac-0001",),
        )
        feature_file, pytest_ref = _write_behavior_assets(tmp_path)
        bdd_example_link_automation(
            tmp_path,
            "task-0001",
            "bdd-0001",
            feature_file,
            "@bdd-junit-test-passes",
            pytest_ref=pytest_ref,
        )

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="BDD Tests" tests="1" failures="0">
    <testcase
      classname="tests.test_task_management_plan_gates"
      file="tests/test_task_management_plan_gates.py"
      name="test_agent_cannot_start_implementation_before_plan_approval">
    </testcase>
  </testsuite>
</testsuites>"""
        report_path = tmp_path / "junit.xml"
        report_path.write_text(xml_content)

        command = (
            "pytest tests/test_task_management_plan_gates.py "
            "--junitxml=reports/behavior/task-management-plan-gates-junit.xml"
        )
        result = import_bdd_report(
            tmp_path,
            "task-0001",
            str(report_path),
            "junit-xml",
            command,
        )

        assert result["format"] == "junit-xml"
        assert result["result"] == "passed"
        assert "bdd-0001" in result["matched_examples"]
        assert result["validation_checks"][0]["status"] == "pass"
        evidence = result["validation_checks"][0]["evidence"]
        assert "pytest_file: tests/test_task_management_plan_gates.py" in evidence
        assert f"pytest_nodeid: {pytest_ref}" in evidence
        assert (
            "feature_file: specs/behavior/features/task-management/plan-gates.feature"
            in evidence
        )

    # sw: f=specs/behavior/features/bdd_report_import/bdd-report-import.feature
    # sw: s=@bdd-bdd-report-import-junit-failure-remains-failed
    def test_import_failing_junit_report(self, tmp_path) -> None:
        """Test importing a failing JUnit XML report."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="JUnit test fails",
            given=("x",),
            when=("y",),
            then=("z",),
            acceptance_criteria=("ac-0001",),
        )
        feature_file, pytest_ref = _write_behavior_assets(tmp_path)
        bdd_example_link_automation(
            tmp_path,
            "task-0001",
            "bdd-0001",
            feature_file,
            "JUnit test fails",
            pytest_ref=pytest_ref,
        )

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="BDD Tests" tests="1" failures="1">
    <testcase
      classname="tests.test_task_management_plan_gates"
      file="tests/test_task_management_plan_gates.py"
      name="test_agent_cannot_start_implementation_before_plan_approval">
      <failure message="AssertionError">Expected X but got Y</failure>
    </testcase>
  </testsuite>
</testsuites>"""
        report_path = tmp_path / "junit.xml"
        report_path.write_text(xml_content)

        result = import_bdd_report(tmp_path, "task-0001", str(report_path), "junit-xml")

        assert result["result"] == "failed"
        assert result["validation_checks"][0]["status"] == "fail"
        assert result["validation_checks"][0]["example_id"] == "bdd-0001"

    def test_import_junit_with_testsuite_root(self, tmp_path) -> None:
        """Test importing JUnit XML with testsuite as root element."""
        bdd_init(tmp_path, "task-0001", "Test feature")
        bdd_example_add(
            tmp_path,
            "task-0001",
            title="Direct suite test",
            given=("x",),
            when=("y",),
            then=("z",),
        )

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="BDD Tests" tests="1" failures="0">
  <testcase name="Direct suite test" classname="test_bdd">
  </testcase>
</testsuite>"""
        report_path = tmp_path / "junit.xml"
        report_path.write_text(xml_content)

        result = import_bdd_report(tmp_path, "task-0001", str(report_path), "junit-xml")

        assert result["result"] == "passed"

    def test_import_invalid_xml(self, tmp_path) -> None:
        """Test importing invalid XML."""
        report_path = tmp_path / "bad.xml"
        report_path.write_text("not xml <><><>")
        with pytest.raises(LaunchError, match="Invalid JUnit XML"):
            import_bdd_report(tmp_path, "task-0001", str(report_path), "junit-xml")


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
