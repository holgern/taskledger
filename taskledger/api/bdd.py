"""BDD API functions for taskledger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from taskledger.domain.bdd import (
    BddAutomationRef,
    BddExampleRecord,
    BddExampleStatus,
    BddFeatureRecord,
    BddRuleRecord,
)
from taskledger.errors import LaunchError
from taskledger.storage.task_store import (
    load_bdd_examples,
    load_bdd_feature,
    load_bdd_reports,
    load_bdd_rules,
    resolve_bdd_example,
    resolve_bdd_rule,
    resolve_plan,
    resolve_task,
    save_bdd_example,
    save_bdd_feature,
    save_bdd_rule,
)
from taskledger.timeutils import utc_now_iso


def _next_id(items: list[Any], prefix: str) -> str:
    """Generate the next sequential ID for a collection."""
    max_num = 0
    for item in items:
        item_id = item.id if hasattr(item, "id") else ""
        if item_id.startswith(prefix + "-"):
            try:
                num = int(item_id.split("-", 1)[1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"{prefix}-{max_num + 1:04d}"


def _resolve_criterion_in_plan(
    criterion_ref: str, plan_criteria: dict[str, str]
) -> str | None:
    """Match a criterion ref against accepted-plan criterion ids.

    ``plan_criteria`` maps lowercased criterion id to its canonical id.
    Matches exact id (case-insensitive) and ``<prefix>-<int>`` forms so
    ``ac-1`` resolves to ``ac-0001``.
    """
    ref = criterion_ref.strip().lower()
    if ref in plan_criteria:
        return plan_criteria[ref]
    ref_parts = ref.split("-", 1)
    if len(ref_parts) != 2:
        return None
    for c_id_lower, canonical in plan_criteria.items():
        parts = c_id_lower.split("-", 1)
        if len(parts) != 2 or parts[0] != ref_parts[0]:
            continue
        try:
            if int(parts[1]) == int(ref_parts[1]):
                return canonical
        except ValueError:
            continue
    return None


def _validate_acceptance_criteria(
    workspace_root: Path,
    task_id: str,
    criteria: tuple[str, ...],
) -> list[str]:
    """Validate acceptance-criterion refs (Finding 7).

    Returns warning strings for criteria that could not be verified because
    no plan is accepted yet (early discovery stays allowed). Raises
    LaunchError when a criterion is not present in the accepted plan, so
    typos cannot pollute automation evidence.
    """
    warnings: list[str] = []
    if not criteria:
        return warnings
    # A resolvable task with an accepted plan enables strict validation;
    # anything else (no task record, no accepted plan, no plan file) keeps
    # early BDD discovery allowed with a warning.
    try:
        task = resolve_task(workspace_root, task_id)
    except LaunchError:
        task = None
    accepted_plan_version = task.accepted_plan_version if task else None
    if accepted_plan_version is None:
        for criterion_id in criteria:
            warnings.append(
                f"Acceptance criterion {criterion_id} could not be verified: "
                "no accepted plan yet."
            )
        return warnings
    try:
        plan = resolve_plan(workspace_root, task_id, version=accepted_plan_version)
    except LaunchError:
        for criterion_id in criteria:
            warnings.append(
                f"Acceptance criterion {criterion_id} could not be verified: "
                "accepted plan not found."
            )
        return warnings
    plan_criteria = {c.id.lower(): c.id for c in plan.criteria}
    if not plan_criteria:
        warnings.append("Accepted plan has no acceptance criteria defined.")
        return warnings
    for criterion_id in criteria:
        if _resolve_criterion_in_plan(criterion_id, plan_criteria) is None:
            raise LaunchError(
                f"Acceptance criterion {criterion_id} is not in the accepted "
                f"plan v{accepted_plan_version}."
            )
    return warnings


def bdd_init(
    workspace_root: Path,
    task_id: str,
    title: str,
    description: str = "",
) -> dict[str, Any]:
    """Initialize BDD for a task by creating a feature record."""
    existing = load_bdd_feature(workspace_root, task_id)
    if existing is not None:
        raise LaunchError(
            f"BDD already initialized for {task_id}. Feature: {existing.title}"
        )

    feature = BddFeatureRecord(
        id="feature-0001",
        task_id=task_id,
        title=title,
        description=description,
    )
    save_bdd_feature(workspace_root, feature)
    return {
        "kind": "bdd_init",
        "task_id": task_id,
        "feature": feature.to_dict(),
    }


def bdd_status(workspace_root: Path, task_id: str) -> dict[str, Any]:
    """Get BDD status for a task."""
    feature = load_bdd_feature(workspace_root, task_id)
    rules = load_bdd_rules(workspace_root, task_id)
    examples = load_bdd_examples(workspace_root, task_id)
    reports = load_bdd_reports(workspace_root, task_id)

    examples_by_status: dict[str, int] = {}
    for ex in examples:
        examples_by_status[ex.status] = examples_by_status.get(ex.status, 0) + 1

    return {
        "kind": "bdd_status",
        "task_id": task_id,
        "feature_title": feature.title if feature else None,
        "rule_count": len(rules),
        "example_count": len(examples),
        "report_count": len(reports),
        "examples_by_status": examples_by_status,
    }


def bdd_rule_add(
    workspace_root: Path,
    task_id: str,
    title: str,
    description: str = "",
    feature_id: str = "bdd",
) -> dict[str, Any]:
    """Add a BDD rule."""
    rules = load_bdd_rules(workspace_root, task_id)
    rule_id = _next_id(rules, "rule")
    rule = BddRuleRecord(
        id=rule_id,
        task_id=task_id,
        title=title,
        description=description,
        feature_id=feature_id,
    )
    save_bdd_rule(workspace_root, rule)
    return {
        "kind": "bdd_rule",
        "task_id": task_id,
        "rule": rule.to_dict(),
    }


def bdd_rule_list(workspace_root: Path, task_id: str) -> dict[str, Any]:
    """List BDD rules."""
    rules = load_bdd_rules(workspace_root, task_id)
    return {
        "kind": "bdd_rule_list",
        "task_id": task_id,
        "rules": [r.to_dict() for r in rules],
    }


def bdd_rule_show(workspace_root: Path, task_id: str, rule_id: str) -> dict[str, Any]:
    """Show a BDD rule."""
    rule = resolve_bdd_rule(workspace_root, task_id, rule_id)
    return {
        "kind": "bdd_rule",
        "task_id": task_id,
        "rule": rule.to_dict(),
    }


def bdd_example_add(
    workspace_root: Path,
    task_id: str,
    title: str,
    rule_id: str | None = None,
    given: tuple[str, ...] = (),
    when: tuple[str, ...] = (),
    then: tuple[str, ...] = (),
    acceptance_criteria: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Add a BDD example."""
    # Finding 7: validate rule and acceptance-criterion refs early so typos
    # cannot pollute automation evidence. Early discovery (no accepted plan)
    # stays allowed with a payload warning.
    if rule_id:
        resolve_bdd_rule(workspace_root, task_id, rule_id)
    warnings = _validate_acceptance_criteria(
        workspace_root, task_id, acceptance_criteria
    )

    examples = load_bdd_examples(workspace_root, task_id)
    example_id = _next_id(examples, "bdd")

    # Determine initial status
    status: BddExampleStatus = "discovered"
    if given or when or then:
        status = "formulated"
    if acceptance_criteria:
        status = "linked"

    example = BddExampleRecord(
        id=example_id,
        task_id=task_id,
        title=title,
        rule_id=rule_id,
        status=status,
        given=given,
        when=when,
        then=then,
        acceptance_criteria=acceptance_criteria,
    )
    save_bdd_example(workspace_root, example)
    return {
        "kind": "bdd_example",
        "task_id": task_id,
        "example": example.to_dict(),
        "warnings": warnings,
    }


def bdd_example_list(workspace_root: Path, task_id: str) -> dict[str, Any]:
    """List BDD examples."""
    examples = load_bdd_examples(workspace_root, task_id)
    return {
        "kind": "bdd_example_list",
        "task_id": task_id,
        "examples": [e.to_dict() for e in examples],
    }


def bdd_example_show(
    workspace_root: Path, task_id: str, example_id: str
) -> dict[str, Any]:
    """Show a BDD example."""
    example = resolve_bdd_example(workspace_root, task_id, example_id)
    return {
        "kind": "bdd_example",
        "task_id": task_id,
        "example": example.to_dict(),
    }


def bdd_example_link_ac(
    workspace_root: Path,
    task_id: str,
    example_id: str,
    criterion_id: str,
) -> dict[str, Any]:
    """Link a BDD example to an acceptance criterion."""
    # Finding 7: validate the criterion ref against the accepted plan.
    warnings = _validate_acceptance_criteria(workspace_root, task_id, (criterion_id,))
    example = resolve_bdd_example(workspace_root, task_id, example_id)
    current_ac = list(example.acceptance_criteria)
    if criterion_id not in current_ac:
        current_ac.append(criterion_id)

    # Determine new status
    new_status = example.status
    if current_ac and example.status in ("discovered", "formulated"):
        new_status = "linked"

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
        acceptance_criteria=tuple(current_ac),
        question_refs=example.question_refs,
        todo_refs=example.todo_refs,
        file_refs=example.file_refs,
        archledger_refs=example.archledger_refs,
        automation=example.automation,
        file_version=example.file_version,
        schema_version=example.schema_version,
        object_type=example.object_type,
        created_at=example.created_at,
        updated_at=utc_now_iso(),
    )
    save_bdd_example(workspace_root, updated)
    return {
        "kind": "bdd_example",
        "task_id": task_id,
        "example": updated.to_dict(),
        "warnings": warnings,
    }


def bdd_example_link_archledger(
    workspace_root: Path,
    task_id: str,
    example_id: str,
    archledger_ref: str,
) -> dict[str, Any]:
    """Link a BDD example to an Archledger record."""
    example = resolve_bdd_example(workspace_root, task_id, example_id)
    current_refs = list(example.archledger_refs)
    if archledger_ref not in current_refs:
        current_refs.append(archledger_ref)

    updated = BddExampleRecord(
        id=example.id,
        task_id=example.task_id,
        title=example.title,
        rule_id=example.rule_id,
        status=example.status,
        given=example.given,
        when=example.when,
        then=example.then,
        tags=example.tags,
        acceptance_criteria=example.acceptance_criteria,
        question_refs=example.question_refs,
        todo_refs=example.todo_refs,
        file_refs=example.file_refs,
        archledger_refs=tuple(current_refs),
        automation=example.automation,
        file_version=example.file_version,
        schema_version=example.schema_version,
        object_type=example.object_type,
        created_at=example.created_at,
        updated_at=utc_now_iso(),
    )
    save_bdd_example(workspace_root, updated)
    return {
        "kind": "bdd_example",
        "task_id": task_id,
        "example": updated.to_dict(),
    }


def bdd_example_link_automation(
    workspace_root: Path,
    task_id: str,
    example_id: str,
    feature_file: str,
    scenario: str = "",
) -> dict[str, Any]:
    """Record the automation feature file for a BDD example (Finding 5, Option A).

    Keeps ``gherkin-export`` pure/derived while letting the Archledger
    candidate carry ``source_refs``/``test_refs`` for the recorded feature
    file. Automation status is preserved; it is advanced to ``automated`` by
    report import, not by recording a path.
    """
    feature_file_clean = feature_file.strip()
    if not feature_file_clean:
        raise LaunchError("Feature file path is required.")
    example = resolve_bdd_example(workspace_root, task_id, example_id)
    scenario_clean = scenario.strip() or example.automation.scenario
    new_automation = BddAutomationRef(
        status=example.automation.status,
        feature_file=feature_file_clean,
        scenario=scenario_clean,
        command=example.automation.command,
        report_path=example.automation.report_path,
    )
    updated = BddExampleRecord(
        id=example.id,
        task_id=example.task_id,
        title=example.title,
        rule_id=example.rule_id,
        status=example.status,
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
    return {
        "kind": "bdd_example",
        "task_id": task_id,
        "example": updated.to_dict(),
    }


def bdd_gherkin_export(
    workspace_root: Path,
    task_id: str,
    out: str,
) -> dict[str, Any]:
    """Export BDD examples as Gherkin .feature file."""
    from taskledger.services.bdd_gherkin import export_gherkin

    return export_gherkin(workspace_root, task_id, out)


def bdd_archledger_candidate(
    workspace_root: Path,
    task_id: str,
    example_id: str,
    out: str = "",
) -> dict[str, Any]:
    """Generate an Archledger behavior record candidate from a BDD example."""
    example = resolve_bdd_example(workspace_root, task_id, example_id)

    # Determine suggested type
    suggested_type = "quality_scenario"
    if any(
        keyword in example.title.lower()
        for keyword in ("lifecycle", "gate", "approval", "lock", "contract")
    ):
        suggested_type = "runtime_scenario"

    # Build candidate content with YAML front matter
    lines = [
        "---",
        f"type: {suggested_type}",
        "status: proposed",
        f"title: {example.title}",
    ]
    if example.automation.feature_file:
        lines.append("source_refs:")
        lines.append(f"  - path: {example.automation.feature_file}")
        lines.append("    role: documents")
        lines.append("test_refs:")
        lines.append(f"  - path: {example.automation.feature_file}")
        lines.append("    kind: bdd")
    lines.append("bdd:")
    feature_rec = load_bdd_feature(workspace_root, task_id)
    lines.append(f"  feature: {feature_rec.title if feature_rec else ''}")
    rule = None
    if example.rule_id:
        rule = resolve_bdd_rule(workspace_root, task_id, example.rule_id)
    if rule:
        lines.append(f"  rule: {rule.title}")
    lines.append(f"  scenario: {example.title}")
    lines.append("  tags:")
    lines.append(f"    - {task_id}")
    lines.append(f"    - {example.id}")
    lines.append("  task_refs:")
    lines.append(f"    - {task_id}")
    if example.acceptance_criteria:
        lines.append("  acceptance_criteria:")
        for ac in example.acceptance_criteria:
            lines.append(f"    - {ac}")
    if example.given:
        lines.append("  given:")
        for step in example.given:
            lines.append(f"    - {step}")
    if example.when:
        lines.append("  when:")
        for step in example.when:
            lines.append(f"    - {step}")
    if example.then:
        lines.append("  then:")
        for step in example.then:
            lines.append(f"    - {step}")
    if example.automation.feature_file:
        lines.append("  automation:")
        lines.append(f"    status: {example.automation.status}")
        lines.append(f"    feature_file: {example.automation.feature_file}")
        lines.append(f"    scenario: {example.title}")
    lines.append("---")

    content = "\n".join(lines)

    # Write to file if out is specified
    if out:
        out_path = Path(out)
        if not out_path.is_absolute():
            out_path = workspace_root / out_path
        # Security: refuse paths outside workspace
        try:
            out_path.resolve().relative_to(workspace_root.resolve())
        except ValueError:
            raise LaunchError(f"Output path must be within workspace: {out}") from None
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content + "\n", encoding="utf-8")

    candidate = {
        "suggested_type": suggested_type,
        "title": example.title,
        "task_refs": [task_id],
        "acceptance_criteria": list(example.acceptance_criteria),
        "feature_file": example.automation.feature_file,
        "content": content,
    }

    return {
        "kind": "bdd_archledger_candidate",
        "task_id": task_id,
        "example_id": example_id,
        "out": out,
        "candidate": candidate,
    }


def import_bdd_report(
    workspace_root: Path,
    task_id: str,
    source_path: str,
    format: str,
    command: str = "",
) -> dict[str, Any]:
    """Import a BDD report and persist validation checks.

    Requires an active validation run. For each matched scenario
    with linked acceptance criteria, persists a validation check
    through the normal validation flow.
    """
    from taskledger.api.task_runs import add_validation_check
    from taskledger.services.bdd_reports import import_bdd_report as _import_bdd_report

    # Run the core import (parsing, matching, example updates, report save)
    result = _import_bdd_report(workspace_root, task_id, source_path, format, command)

    # Persist validation checks for matched scenarios with linked criteria.
    # Finding 2: persistence failures for linked criteria must surface, not be
    # silently swallowed into an empty validation_checks list. Finding 4:
    # preserve rich check metadata (name/details/evidence/command/report path).
    linked_checks: list[dict[str, Any]] = list(result.get("validation_checks", []))
    persisted_check_ids: list[str] = []
    persisted_checks: list[dict[str, Any]] = []
    for check_info in linked_checks:
        criterion_id = check_info.get("criterion_id")
        if not criterion_id:
            continue
        try:
            run = add_validation_check(
                workspace_root,
                task_id,
                name=str(check_info.get("name") or f"BDD: {source_path}"),
                criterion_id=str(criterion_id),
                status=str(check_info.get("status") or "fail"),
                details=check_info.get("details"),
                evidence=tuple(
                    check_info.get("evidence") or (f"report: {source_path}",)
                ),
            )
        except LaunchError as exc:
            raise LaunchError(
                "BDD report matched linked acceptance criteria, but validation "
                f"check persistence failed: {exc}"
            ) from exc
        # The last check in the run is the one we just added.
        check_id = run.checks[-1].id if run.checks else None
        if check_id:
            persisted_check_ids.append(check_id)
        persisted_checks.append(
            {
                "check_id": check_id,
                "criterion_id": check_info.get("criterion_id"),
                "status": check_info.get("status"),
                "example_id": check_info.get("example_id"),
            }
        )

    # Update the saved BDD report record with persisted check IDs.
    if persisted_check_ids:
        from taskledger.storage.task_store import load_bdd_reports, save_bdd_report

        reports = load_bdd_reports(workspace_root, task_id)
        for report in reports:
            if report.id == result.get("report_id"):
                updated_report = report.__class__(
                    id=report.id,
                    task_id=report.task_id,
                    source_path=report.source_path,
                    format=report.format,
                    command=report.command,
                    imported_at=report.imported_at,
                    result=report.result,
                    example_results=report.example_results,
                    validation_check_refs=tuple(persisted_check_ids),
                    unmatched_count=report.unmatched_count,
                    has_unmatched_failures=report.has_unmatched_failures,
                    file_version=report.file_version,
                    schema_version=report.schema_version,
                    object_type=report.object_type,
                    created_at=report.created_at,
                )
                save_bdd_report(workspace_root, updated_report)
                break

    result["validation_checks"] = persisted_checks
    return result
