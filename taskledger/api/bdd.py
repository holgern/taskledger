"""BDD API functions for taskledger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from taskledger.domain.bdd import (
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

    # Persist validation checks for matched scenarios with linked criteria
    persisted_check_ids: list[str] = []
    for check_info in result.get("validation_checks", []):
        criterion_id = check_info.get("criterion_id")
        status = check_info.get("status", "pass")
        if not criterion_id:
            continue
        try:
            run = add_validation_check(
                workspace_root,
                task_id,
                name=check_info.get("check_id") or f"BDD: {source_path}",
                criterion_id=criterion_id,
                status=status,
                evidence=(f"report: {source_path}",),
            )
            # Find the last check in the run (the one we just added)
            if run.checks:
                last_check = run.checks[-1]
                if last_check.id:
                    persisted_check_ids.append(last_check.id)
        except LaunchError:
            # If validation run is not active, skip persistence
            # but continue with the import result
            pass

    # Update the saved BDD report record with persisted check IDs
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
                    file_version=report.file_version,
                    schema_version=report.schema_version,
                    object_type=report.object_type,
                    created_at=report.created_at,
                )
                save_bdd_report(workspace_root, updated_report)
                break

    # Update result with persisted check IDs
    persisted_checks = [
        {
            "check_id": cid,
            "criterion_id": cinfo.get("criterion_id"),
            "status": cinfo.get("status"),
            "example_id": cinfo.get("example_id"),
        }
        for cid, cinfo in zip(
            persisted_check_ids,
            result.get("validation_checks", []),
            strict=False,
        )
    ]
    result["validation_checks"] = persisted_checks
    return result
