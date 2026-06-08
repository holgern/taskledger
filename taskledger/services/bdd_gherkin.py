"""Gherkin export service for BDD examples."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from taskledger.domain.bdd import BddExampleRecord
from taskledger.errors import LaunchError
from taskledger.storage.task_store import (
    load_bdd_examples,
    load_bdd_feature,
    load_bdd_rules,
)


def export_gherkin(
    workspace_root: Path,
    task_id: str,
    out: str,
) -> dict[str, Any]:
    """Export BDD examples as derived Gherkin .feature output.

    Rules:
    - Refuse export if no formulated/linked/automated/validated examples exist.
    - Warn if examples lack acceptance-criterion links.
    - Warn if the output path suggests deprecated pytest-bdd/Cucumber ownership.
    - Write only under workspace root.
    - Include a derived-output header.
    - Deterministic ordering by rule then example ID.
    """
    # Validate output path
    out_path = Path(out)
    if not out_path.is_absolute():
        out_path = workspace_root / out_path
    try:
        out_path.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        raise LaunchError(f"Output path must be within workspace: {out}") from None
    rel_out = out_path.resolve().relative_to(workspace_root.resolve()).as_posix()

    # Load data
    feature = load_bdd_feature(workspace_root, task_id)
    if feature is None:
        raise LaunchError(f"BDD not initialized for {task_id}. Run 'bdd init' first.")

    examples = load_bdd_examples(workspace_root, task_id)
    exportable_statuses = {"formulated", "linked", "automated", "validated"}
    exportable = [e for e in examples if e.status in exportable_statuses]

    if not exportable:
        raise LaunchError(
            "No formulated BDD examples found. "
            "Add examples with given/when/then steps before exporting."
        )

    rules = load_bdd_rules(workspace_root, task_id)
    rules_by_id = {r.id: r for r in rules}

    # Collect warnings
    warnings: list[str] = []
    warning_details: list[dict[str, object]] = []
    for ex in exportable:
        if not ex.acceptance_criteria:
            warnings.append(f"Example {ex.id} has no acceptance-criterion link.")
    derived_output_warning = _derived_output_warning(rel_out)
    if derived_output_warning is not None:
        details_reasons = derived_output_warning.get("reasons", [])
        if isinstance(details_reasons, list):
            warnings.extend(str(item) for item in details_reasons)
        warning_details.append(derived_output_warning)

    # Group examples by rule
    examples_by_rule: dict[str, list[BddExampleRecord]] = {}
    unruled: list[BddExampleRecord] = []
    for ex in exportable:
        if ex.rule_id and ex.rule_id in rules_by_id:
            examples_by_rule.setdefault(ex.rule_id, []).append(ex)
        else:
            unruled.append(ex)

    # Build Gherkin content
    lines: list[str] = []

    # Ownership header
    lines.append(f"# Generated derived output from Taskledger task {task_id}.")
    lines.append(f"# Source: .taskledger/tasks/{task_id}/bdd/examples/")
    lines.append(
        "# Prefer SpecWeave-owned specs/behavior/features/... "
        "as canonical behavior specs."
    )
    lines.append("# Plain pytest files under tests/ should enforce the behavior.")
    lines.append("")

    # Feature tags
    tags = [f"@{task_id}"]
    if feature.tags:
        tags.extend(f"@{t}" for t in feature.tags)
    lines.append(" ".join(tags))

    # Feature line
    lines.append(f"Feature: {feature.title}")
    lines.append("")

    # Export by rule
    rule_order = sorted(examples_by_rule.keys())
    for rule_id in rule_order:
        rule = rules_by_id[rule_id]
        rule_examples = sorted(examples_by_rule[rule_id], key=lambda e: e.id)

        # Rule tags
        rule_tags = [f"@{rule_id}"]
        if rule.tags:
            rule_tags.extend(f"@{t}" for t in rule.tags)
        lines.append(f"  {' '.join(rule_tags)}")
        lines.append(f"  Rule: {rule.title}")
        lines.append("")

        for ex in rule_examples:
            _append_scenario(lines, ex, indent=4)
        lines.append("")

    # Unruled examples
    if unruled:
        unruled_sorted = sorted(unruled, key=lambda e: e.id)
        for ex in unruled_sorted:
            _append_scenario(lines, ex, indent=2)
        lines.append("")

    content = "\n".join(lines)

    # Write file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    return {
        "kind": "bdd_gherkin_export",
        "task_id": task_id,
        "out": str(out_path),
        "feature": feature.title,
        "exported_examples": [e.id for e in exportable],
        "warnings": warnings,
        "warning_details": warning_details,
    }


def _derived_output_warning(rel_out: str) -> dict[str, object] | None:
    reasons: list[str] = []
    normalized = rel_out.replace("\\", "/")
    filename = Path(normalized).name
    if normalized.startswith("tests/bdd/features/"):
        reasons.append(
            "Deprecated derived-output path: tests/bdd/features/ "
            "suggests pytest-bdd ownership."
        )
    if normalized.startswith("tests/behavior/features/"):
        reasons.append(
            "Deprecated derived-output path: tests/behavior/features/ "
            "suggests test-owned .feature files."
        )
    if normalized.startswith("specs/bdd/features/"):
        reasons.append(
            "Deprecated derived-output path: specs/bdd/features/ "
            "is not the canonical behavior-spec location."
        )
    if re.match(r"^task-\d+", filename):
        reasons.append(
            "Canonical .feature filenames should not start with task-<digits>."
        )
    lower = normalized.lower()
    if any(token in lower for token in ("pytest-bdd", "cucumber", "behave")):
        reasons.append(
            "Derived output path should not imply pytest-bdd, "
            "Cucumber, or Behave ownership."
        )
    if not reasons:
        return None
    return {
        "code": "TLBDD_PATH_DERIVED_NOT_CANONICAL",
        "message": (
            "Taskledger gherkin-export creates derived output. Canonical behavior "
            "specs should live under specs/behavior/features/<area>/<feature>.feature "
            "and should be enforced by plain pytest tests under tests/."
        ),
        "recommended_feature_path_pattern": (
            "specs/behavior/features/<area>/<feature>.feature"
        ),
        "recommended_pytest_path_pattern": "tests/test_<area>_<feature>.py",
        "reasons": reasons,
    }


def _append_scenario(
    lines: list[str],
    example: BddExampleRecord,
    indent: int = 2,
) -> None:
    """Append a scenario block to the Gherkin lines with traceability tags."""
    prefix = " " * indent

    # Tags with traceability info
    scenario_tags = [f"@{example.id}"]
    scenario_tags.append(f"@{example.task_id}")
    if example.rule_id:
        scenario_tags.append(f"@{example.rule_id}")
    if example.tags:
        scenario_tags.extend(f"@{t}" for t in example.tags)
    # Add acceptance criterion tags
    for ac in example.acceptance_criteria:
        scenario_tags.append(f"@{ac}")
    # Add archledger ref tags
    for al_ref in example.archledger_refs:
        scenario_tags.append(f"@{al_ref}")
    lines.append(f"{prefix}{' '.join(scenario_tags)}")

    # Scenario line
    lines.append(f"{prefix}Scenario: {example.title}")

    # Given steps
    for i, step in enumerate(example.given):
        keyword = "Given" if i == 0 else "And"
        lines.append(f"{prefix}  {keyword} {step}")

    # When steps
    for i, step in enumerate(example.when):
        keyword = "When" if i == 0 else "And"
        lines.append(f"{prefix}  {keyword} {step}")

    # Then steps
    for i, step in enumerate(example.then):
        keyword = "Then" if i == 0 else "And"
        lines.append(f"{prefix}  {keyword} {step}")

    lines.append("")
