"""BDD report import service for Cucumber JSON and JUnit XML."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from taskledger.domain.bdd import BddAutomationRef, BddExampleRecord, BddReportRecord
from taskledger.domain.sidecars import ValidationCheck
from taskledger.errors import LaunchError
from taskledger.storage.task_store import (
    load_bdd_examples,
    save_bdd_example,
    save_bdd_report,
)
from taskledger.timeutils import utc_now_iso


def import_bdd_report(
    workspace_root: Path,
    task_id: str,
    source_path: str,
    format: str,
    command: str = "",
) -> dict[str, Any]:
    """Import a BDD report from Cucumber JSON or JUnit XML.

    Args:
        workspace_root: Project workspace root.
        task_id: Task ID.
        source_path: Path to the report file.
        format: Report format: cucumber-json, junit-xml.
        command: The test command that produced the report.

    Returns:
        Import result payload with matched/unmatched scenarios
        and validation check data (checks not persisted here).
    """
    report_file = Path(source_path)
    if not report_file.is_absolute():
        report_file = workspace_root / report_file
    if not report_file.exists():
        raise LaunchError(f"Report file not found: {source_path}")

    # Load task examples for matching
    examples = load_bdd_examples(workspace_root, task_id)

    (
        examples_by_id,
        examples_by_title,
        examples_by_scenario,
        examples_by_pytest_nodeid,
        examples_by_pytest_path,
    ) = _build_example_indices(examples)

    # Parse report based on format
    if format == "cucumber-json":
        scenarios = _parse_cucumber_json(report_file)
    elif format == "junit-xml":
        scenarios = _parse_junit_xml(report_file)
    else:
        raise LaunchError(f"Unsupported report format: {format}")

    # Match scenarios to examples
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    validation_checks: list[ValidationCheck] = []
    imported_at = utc_now_iso()

    for scenario in scenarios:
        scenario_name = scenario.get("name", "")
        status = scenario.get("status", "unknown")
        error_message = scenario.get("error_message", "")
        pytest_path = str(scenario.get("pytest_path", "") or "")
        pytest_nodeid = str(scenario.get("pytest_nodeid", "") or "")
        example = _resolve_example_for_scenario(
            scenario,
            examples_by_id=examples_by_id,
            examples_by_title=examples_by_title,
            examples_by_scenario=examples_by_scenario,
            examples_by_pytest_nodeid=examples_by_pytest_nodeid,
            examples_by_pytest_path=examples_by_pytest_path,
        )

        if example is None:
            unmatched.append(scenario)
            continue

        # Update example automation status
        new_automation = BddAutomationRef(
            status="automated",
            feature_file=example.automation.feature_file,
            scenario=example.automation.scenario or scenario_name,
            pytest_path=example.automation.pytest_path or pytest_path,
            pytest_nodeid=example.automation.pytest_nodeid or pytest_nodeid,
            command=command,
            report_path=source_path,
        )

        # Determine new example status
        new_status = example.status
        if status == "passed" and example.status in ("linked", "automated"):
            new_status = "validated"

        updated = BddExampleRecord(
            id=example.id,
            task_id=example.task_id,
            title=example.title,
            rule_id=example.rule_id,
            status=new_status,
            given=example.given,
            when=example.when,
            then=example.then,
            tags=example.tags,
            acceptance_criteria=example.acceptance_criteria,
            question_refs=example.question_refs,
            todo_refs=example.todo_refs,
            file_refs=example.file_refs,
            archledger_refs=example.archledger_refs,
            automation=new_automation,
            file_version=example.file_version,
            schema_version=example.schema_version,
            object_type=example.object_type,
            created_at=example.created_at,
            updated_at=utc_now_iso(),
        )
        save_bdd_example(workspace_root, updated)

        # Create validation check metadata (not persisted here)
        scenario_ref = example.automation.scenario or scenario_name
        validation_checks.extend(
            _build_validation_checks(
                example=example,
                automation=new_automation,
                source_path=source_path,
                task_id=task_id,
                imported_at=imported_at,
                command=command,
                status=status,
                error_message=error_message,
                scenario_ref=scenario_ref,
            )
        )
        matched.append(_matched_result(example, new_automation, scenario_ref, status))

    # Save report record
    example_results = [_matched_example_result(item, imported_at) for item in matched]
    example_results.extend(
        _unmatched_example_result(item, imported_at) for item in unmatched
    )

    unmatched_count = len(unmatched)
    has_unmatched_failures = any(
        u.get("status", "unknown") != "passed" for u in unmatched
    )

    reports_existing = _count_reports(workspace_root, task_id)
    report_id = f"bdd-report-{reports_existing + 1:04d}"

    report = BddReportRecord(
        id=report_id,
        task_id=task_id,
        source_path=source_path,
        format=format,
        command=command,
        imported_at=imported_at,
        result=_overall_result(matched),
        example_results=tuple(example_results),
        validation_check_refs=(),
        unmatched_count=unmatched_count,
        has_unmatched_failures=has_unmatched_failures,
    )
    save_bdd_report(workspace_root, report)

    return {
        "kind": "bdd_report_import",
        "task_id": task_id,
        "report_id": report_id,
        "format": format,
        "matched_examples": [m["example_id"] for m in matched],
        "unmatched_scenarios": [u.get("name", "") for u in unmatched],
        "validation_checks": [
            {
                "check_id": None,
                "name": c.name,
                "criterion_id": c.criterion_id,
                "status": c.status,
                "details": c.details,
                "evidence": list(c.evidence),
                "example_id": _find_example_for_check(c, matched),
            }
            for c in validation_checks
        ],
        "result": report.result,
        "warnings": [f"Unmatched scenario: {u.get('name', '?')}" for u in unmatched],
        "unmatched_count": unmatched_count,
        "has_unmatched_failures": has_unmatched_failures,
    }


def _match_by_bdd_tag(
    tags: list[str],
    examples_by_id: dict[str, BddExampleRecord],
) -> BddExampleRecord | None:
    """Match a scenario to a BDD example by @bdd-* tag."""
    for tag in tags:
        if tag.startswith("bdd-") or tag.startswith("bdd_"):
            # Strip any leading @ if present
            clean = tag.lstrip("@")
            if clean in examples_by_id:
                return examples_by_id[clean]
    return None


def _match_by_pytest_path(
    pytest_path: str,
    scenario_name: str,
    examples_by_pytest_path: dict[str, list[BddExampleRecord]],
) -> BddExampleRecord | None:
    candidates = examples_by_pytest_path.get(pytest_path, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    for candidate in candidates:
        if scenario_name and candidate.automation.scenario == scenario_name:
            return candidate
        if scenario_name and candidate.title == scenario_name:
            return candidate
    return None


def _build_example_indices(
    examples: list[BddExampleRecord],
) -> tuple[
    dict[str, BddExampleRecord],
    dict[str, BddExampleRecord],
    dict[str, BddExampleRecord],
    dict[str, BddExampleRecord],
    dict[str, list[BddExampleRecord]],
]:
    examples_by_id: dict[str, BddExampleRecord] = {}
    examples_by_title: dict[str, BddExampleRecord] = {}
    examples_by_scenario: dict[str, BddExampleRecord] = {}
    examples_by_pytest_nodeid: dict[str, BddExampleRecord] = {}
    examples_by_pytest_path: dict[str, list[BddExampleRecord]] = {}
    for example in examples:
        examples_by_id[example.id] = example
        examples_by_title[example.title] = example
        if example.automation.scenario:
            examples_by_scenario[example.automation.scenario] = example
        if example.automation.pytest_nodeid:
            examples_by_pytest_nodeid[example.automation.pytest_nodeid] = example
        if example.automation.pytest_path:
            examples_by_pytest_path.setdefault(
                example.automation.pytest_path, []
            ).append(example)
    return (
        examples_by_id,
        examples_by_title,
        examples_by_scenario,
        examples_by_pytest_nodeid,
        examples_by_pytest_path,
    )


def _resolve_example_for_scenario(
    scenario: dict[str, Any],
    *,
    examples_by_id: dict[str, BddExampleRecord],
    examples_by_title: dict[str, BddExampleRecord],
    examples_by_scenario: dict[str, BddExampleRecord],
    examples_by_pytest_nodeid: dict[str, BddExampleRecord],
    examples_by_pytest_path: dict[str, list[BddExampleRecord]],
) -> BddExampleRecord | None:
    scenario_name = str(scenario.get("name", "") or "")
    tags = list(scenario.get("tags", []))
    pytest_path = str(scenario.get("pytest_path", "") or "")
    pytest_nodeid = str(scenario.get("pytest_nodeid", "") or "")
    example = _match_by_bdd_tag(tags, examples_by_id)
    if example is None and pytest_nodeid:
        example = examples_by_pytest_nodeid.get(pytest_nodeid)
    if example is None and pytest_path:
        example = _match_by_pytest_path(
            pytest_path, scenario_name, examples_by_pytest_path
        )
    if example is None:
        example = examples_by_scenario.get(scenario_name)
    if example is None:
        example = examples_by_title.get(scenario_name)
    return example


def _build_validation_checks(
    *,
    example: BddExampleRecord,
    automation: BddAutomationRef,
    source_path: str,
    task_id: str,
    imported_at: str,
    command: str,
    status: str,
    error_message: str,
    scenario_ref: str,
) -> list[ValidationCheck]:
    check_status: str = "pass" if status == "passed" else "fail"
    checks: list[ValidationCheck] = []
    for criterion_id in example.acceptance_criteria:
        checks.append(
            ValidationCheck(
                id=None,
                name=f"BDD: {scenario_ref}",
                criterion_id=criterion_id,
                status=check_status,  # type: ignore[arg-type]
                details=(
                    f"Behavior evidence reported {status}."
                    + (f" Error: {error_message}" if error_message else "")
                ),
                evidence=_build_check_evidence(
                    example=example,
                    automation=automation,
                    source_path=source_path,
                    task_id=task_id,
                    imported_at=imported_at,
                    command=command,
                    status=status,
                    scenario_ref=scenario_ref,
                ),
            )
        )
    return checks


def _build_check_evidence(
    *,
    example: BddExampleRecord,
    automation: BddAutomationRef,
    source_path: str,
    task_id: str,
    imported_at: str,
    command: str,
    status: str,
    scenario_ref: str,
) -> tuple[str, ...]:
    evidence_items = [
        f"report: {source_path}",
        f"scenario: {scenario_ref}",
        f"status: {status}",
        f"task: {task_id}",
        f"imported_at: {imported_at}",
    ]
    if command:
        evidence_items.append(f"command: {command}")
    if example.automation.feature_file:
        evidence_items.append(f"feature_file: {example.automation.feature_file}")
    if automation.pytest_path:
        evidence_items.append(f"pytest_file: {automation.pytest_path}")
    if automation.pytest_nodeid:
        evidence_items.append(f"pytest_nodeid: {automation.pytest_nodeid}")
    return tuple(evidence_items)


def _matched_result(
    example: BddExampleRecord,
    automation: BddAutomationRef,
    scenario_ref: str,
    status: str,
) -> dict[str, Any]:
    return {
        "example_id": example.id,
        "scenario": scenario_ref,
        "status": status,
        "criterion_ids": list(example.acceptance_criteria),
        "feature_file": example.automation.feature_file,
        "pytest_path": automation.pytest_path,
        "pytest_nodeid": automation.pytest_nodeid,
    }


def _matched_example_result(
    matched: dict[str, Any], imported_at: str
) -> dict[str, Any]:
    return {
        "example_id": matched["example_id"],
        "scenario": matched["scenario"],
        "status": matched["status"],
        "feature_file": matched.get("feature_file", ""),
        "pytest_path": matched.get("pytest_path", ""),
        "pytest_nodeid": matched.get("pytest_nodeid", ""),
        "acceptance_criteria": matched.get("criterion_ids", []),
        "matched": True,
        "imported_at": imported_at,
    }


def _unmatched_example_result(
    unmatched: dict[str, Any], imported_at: str
) -> dict[str, Any]:
    return {
        "scenario": unmatched.get("name", ""),
        "status": unmatched.get("status", "unknown"),
        "pytest_path": unmatched.get("pytest_path", ""),
        "pytest_nodeid": unmatched.get("pytest_nodeid", ""),
        "matched": False,
        "imported_at": imported_at,
    }


def _parse_cucumber_json(path: Path) -> list[dict[str, Any]]:
    """Parse a Cucumber JSON report file, extracting tags."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LaunchError(f"Invalid Cucumber JSON: {exc}") from exc

    if not isinstance(data, list):
        raise LaunchError("Invalid Cucumber JSON: expected array of feature objects.")

    scenarios: list[dict[str, Any]] = []
    for feature in data:
        if not isinstance(feature, dict):
            continue
        elements = feature.get("elements", [])
        if not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            # Only process scenarios, not backgrounds
            if element.get("type") != "scenario":
                continue

            name = element.get("name", "")
            steps = element.get("steps", [])

            # Extract tags from element-level tags
            tags: list[str] = []
            raw_tags = element.get("tags", [])
            if isinstance(raw_tags, list):
                for t in raw_tags:
                    if isinstance(t, dict):
                        tag_name = t.get("name", "")
                        if isinstance(tag_name, str):
                            tags.append(tag_name.lstrip("@"))
                    elif isinstance(t, str):
                        tags.append(t.lstrip("@"))

            # Determine status from steps. Any non-`passed` step fails the
            # scenario: failed/ambiguous/error are hard failures, while
            # skipped/pending/undefined/unknown are treated as non-passing so
            # they can never satisfy an acceptance criterion (Finding 1).
            status = "passed"
            error_message = ""
            for step in steps:
                if not isinstance(step, dict):
                    continue
                result = step.get("result", {})
                if not isinstance(result, dict):
                    continue
                step_status = str(result.get("status", "passed")).strip().lower()
                if step_status == "passed":
                    continue
                status = step_status or "unknown"
                error_message = str(result.get("error_message", ""))
                break

            scenarios.append(
                {
                    "name": name,
                    "status": status,
                    "error_message": error_message,
                    "feature_name": feature.get("name", ""),
                    "tags": tags,
                }
            )

    return scenarios


def _parse_junit_xml(path: Path) -> list[dict[str, Any]]:
    """Parse a JUnit XML report file."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise LaunchError(f"Invalid JUnit XML: {exc}") from exc

    root = tree.getroot()

    scenarios: list[dict[str, Any]] = []

    # Handle both <testsuites> and <testsuite> as root
    if root.tag == "testsuites":
        test_suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        test_suites = [root]
    else:
        raise LaunchError(f"Invalid JUnit XML: unexpected root element <{root.tag}>")

    for suite in test_suites:
        suite_name = suite.get("name", "")
        for testcase in suite.findall("testcase"):
            name = testcase.get("name", "")
            classname = testcase.get("classname", "")
            pytest_path = testcase.get("file", "") or _pytest_path_from_classname(
                classname
            )
            pytest_nodeid = _pytest_nodeid_from_case(pytest_path, classname, name)

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if failure is not None:
                status = "failed"
                error_message = failure.get("message", "")
            elif error is not None:
                status = "error"
                error_message = error.get("message", "")
            elif skipped is not None:
                message = (skipped.get("message", "") or "").lower()
                status = "xfailed" if "xfail" in message else "skipped"
                error_message = skipped.get("message", "")
            else:
                status = "passed"
                error_message = ""

            scenarios.append(
                {
                    "name": name,
                    "status": status,
                    "error_message": error_message,
                    "feature_name": suite_name,
                    "classname": classname,
                    "pytest_path": pytest_path,
                    "pytest_nodeid": pytest_nodeid,
                    "tags": [],
                }
            )

    return scenarios


def _overall_result(matched: list[dict[str, Any]]) -> str:
    """Determine overall result from matched scenarios."""
    if not matched:
        return "unknown"
    if all(m.get("status") == "passed" for m in matched):
        return "passed"
    return "failed"


def _find_example_for_check(
    check: ValidationCheck,
    matched: list[dict[str, Any]],
) -> str | None:
    """Find the example ID for a validation check."""
    for m in matched:
        if check.criterion_id in m.get("criterion_ids", []):
            return m.get("example_id")
    return None


def _count_reports(workspace_root: Path, task_id: str) -> int:
    """Count existing BDD reports for a task."""
    from taskledger.storage.task_store import load_bdd_reports

    return len(load_bdd_reports(workspace_root, task_id))


def _pytest_path_from_classname(classname: str) -> str:
    if not classname:
        return ""
    parts = classname.split(".")
    if len(parts) > 1 and parts[-1].startswith("Test"):
        parts = parts[:-1]
    if not parts or not parts[-1].startswith("test_"):
        return ""
    return "/".join(parts) + ".py"


def _pytest_nodeid_from_case(pytest_path: str, classname: str, name: str) -> str:
    if not pytest_path or not name:
        return ""
    class_name = ""
    if classname:
        parts = classname.split(".")
        if len(parts) > 1 and parts[-1].startswith("Test"):
            class_name = parts[-1]
    if class_name:
        return f"{pytest_path}::{class_name}::{name}"
    return f"{pytest_path}::{name}"
