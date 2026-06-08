"""Derived JSON export for task-local BDD/example data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from taskledger.storage.task_store import (
    load_bdd_examples,
    load_bdd_feature,
    load_bdd_rules,
)


def build_bdd_export_payload(workspace_root: Path, task_id: str) -> dict[str, Any]:
    """Build stable JSON exchange data for task-local BDD records."""
    feature = load_bdd_feature(workspace_root, task_id)
    rules = load_bdd_rules(workspace_root, task_id)
    examples = load_bdd_examples(workspace_root, task_id)

    rules_payload = [
        {
            "id": rule.id,
            "title": rule.title,
            "description": rule.description,
        }
        for rule in rules
    ]
    examples_payload = []
    external_specs: dict[str, dict[str, Any]] = {}
    for example in examples:
        examples_payload.append(
            {
                "id": example.id,
                "title": example.title,
                "rule_id": example.rule_id,
                "given": list(example.given),
                "when": list(example.when),
                "then": list(example.then),
                "acceptance_criteria": list(example.acceptance_criteria),
                "traceability_tags": [
                    f"@{tag}"
                    for tag in (
                        example.task_id,
                        example.id,
                        *example.acceptance_criteria,
                    )
                    if tag
                ],
            }
        )
        automation = example.automation
        if not any(
            (
                automation.feature_file,
                automation.scenario,
                automation.pytest_path,
                automation.pytest_nodeid,
            )
        ):
            continue
        feature_path = automation.feature_file or ""
        spec_entry = external_specs.setdefault(
            feature_path,
            {
                "path": feature_path,
                "scenario_tags": [],
                "pytest_tests": [],
            },
        )
        scenario_tags = spec_entry["scenario_tags"]
        assert isinstance(scenario_tags, list)
        if automation.scenario and automation.scenario not in scenario_tags:
            scenario_tags.append(automation.scenario)
        pytest_tests = spec_entry["pytest_tests"]
        assert isinstance(pytest_tests, list)
        pytest_ref = {
            "path": automation.pytest_path,
            "nodeid": automation.pytest_nodeid,
        }
        if any(pytest_ref.values()) and pytest_ref not in pytest_tests:
            pytest_tests.append(pytest_ref)

    return {
        "schema_version": 1,
        "producer": "taskledger",
        "kind": "task_bdd_spec",
        "task_id": task_id,
        "ownership": {
            "canonical_behavior_specs": (
                "specs/behavior/features/<area>/<feature>.feature"
            ),
            "canonical_behavior_owner": "SpecWeave",
            "taskledger_role": "task-local planning and evidence overlay",
        },
        "feature": feature.title if feature else "",
        "rules": rules_payload,
        "examples": examples_payload,
        "external_behavior_specs": list(external_specs.values()),
    }
