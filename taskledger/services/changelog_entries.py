from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from taskledger.domain.models import (
    CHANGELOG_CATEGORIES,
    CHANGELOG_STATUSES,
    ActorRef,
    ChangelogEntry,
    normalize_changelog_category,
    normalize_changelog_status,
)
from taskledger.errors import LaunchError
from taskledger.ids import next_project_id
from taskledger.services.actors import resolve_actor
from taskledger.services.releases import build_changelog_context
from taskledger.storage.frontmatter import read_markdown_front_matter
from taskledger.storage.task_store import (
    changelog_entry_markdown_path,
    list_changes,
    list_plans,
    list_runs,
    list_tasks,
    load_changelog_entries,
    load_todos,
    resolve_release,
    resolve_task,
    resolve_v2_paths,
    save_changelog_entry,
    task_changelog_dir,
    task_numeric_sort_key,
)
from taskledger.timeutils import utc_now_iso

SUMMARY_MAX_CHARS = 180
SUMMARY_WARN_CHARS = 120
_SUMMARY_ACTION_PREFIXES: tuple[str, ...] = (
    "Added ",
    "Changed ",
    "Deprecated ",
    "Removed ",
    "Fixed ",
    "Secured ",
    "Documented ",
    "Improved ",
)


@dataclass(frozen=True, slots=True)
class ChangelogVersionScope:
    version: str
    since_version: str | None
    since_task_id: str
    until_task_id: str
    range_mode: str
    task_ids: tuple[str, ...]
    omitted_task_ids: tuple[str, ...]


def resolve_changelog_version_scope(
    workspace_root: Path,
    *,
    version: str,
) -> ChangelogVersionScope:
    release = resolve_release(workspace_root, version)
    until_task_id = release.boundary_task_id
    since_version = release.previous_version
    since_task: str | None = None
    from_task: str | None = None
    if since_version is None:
        from_task = _first_task_in_range(workspace_root, until_task_id)

    payload = cast(
        dict[str, object],
        build_changelog_context(
            workspace_root,
            version=version,
            since_version=since_version,
            since_task=since_task,
            from_task=from_task,
            until_task=until_task_id,
            format_name="json",
        ),
    )
    tasks = _dict_list(payload.get("tasks"))
    omitted = _dict_list(payload.get("omitted_tasks"))
    return ChangelogVersionScope(
        version=version,
        since_version=cast(str | None, payload.get("since_version")),
        since_task_id=str(payload.get("since_task_id") or ""),
        until_task_id=str(payload.get("until_task_id") or until_task_id),
        range_mode=str(payload.get("range_mode") or "since_version"),
        task_ids=tuple(str(item.get("task_id") or "") for item in tasks),
        omitted_task_ids=tuple(str(item.get("task_id") or "") for item in omitted),
    )


def list_changelog_entries(
    workspace_root: Path,
    *,
    task_ref: str | None = None,
    version: str | None = None,
    include_statuses: tuple[str, ...] = ("accepted",),
) -> list[ChangelogEntry]:
    if task_ref is not None and version is not None:
        raise LaunchError("Use either --task or --version, not both.")
    if task_ref is None and version is None:
        raise LaunchError("Provide --task or --version.")
    statuses = _normalize_status_filter(include_statuses)
    if task_ref is not None:
        task = resolve_task(workspace_root, task_ref)
        task_entries = load_changelog_entries(workspace_root, task.id)
        return sorted(
            [entry for entry in task_entries if entry.status in statuses],
            key=lambda entry: entry.entry_id,
        )
    assert version is not None
    scope = resolve_changelog_version_scope(workspace_root, version=version)
    version_entries: list[ChangelogEntry] = []
    for task_id in scope.task_ids:
        version_entries.extend(load_changelog_entries(workspace_root, task_id))
    return sorted(
        [entry for entry in version_entries if entry.status in statuses],
        key=lambda entry: (task_numeric_sort_key(entry.task_id), entry.entry_id),
    )


def add_changelog_entry(
    workspace_root: Path,
    task_ref: str,
    *,
    category: str,
    summary: str,
    body: str = "",
    release_version: str | None = None,
    status: str = "accepted",
    audience: str | None = None,
    scopes: tuple[str, ...] = (),
    source_run_id: str | None = None,
    source_kind: str | None = None,
    dry_run: bool = False,
) -> ChangelogEntry:
    task = resolve_task(workspace_root, task_ref)
    normalized_category = normalize_changelog_category(category)
    normalized_status = normalize_changelog_status(status)
    cleaned_summary = summary.strip()
    if not cleaned_summary:
        raise LaunchError("Changelog summary must not be empty.")
    assert_changelog_summary_valid(cleaned_summary, fail_on_warning=True)
    _assert_source_run_belongs_to_task(workspace_root, task.id, source_run_id)
    existing_ids = [
        entry.entry_id for entry in load_changelog_entries(workspace_root, task.id)
    ]
    entry_id = next_project_id("cle", existing_ids)
    entry = ChangelogEntry(
        entry_id=entry_id,
        task_id=task.id,
        category=normalized_category,
        summary=cleaned_summary,
        body=body.strip(),
        status=normalized_status,
        release_version=release_version,
        audience=audience,
        scopes=tuple(scope.strip() for scope in scopes if scope.strip()),
        source_run_id=source_run_id,
        source_kind=source_kind,
        created_by=resolve_actor(workspace_root=workspace_root),
    )
    if not dry_run:
        save_changelog_entry(workspace_root, entry)
    return entry


def import_changelog_entry_file(
    workspace_root: Path,
    task_ref: str,
    source_path: Path,
    *,
    replace: bool = False,
) -> ChangelogEntry:
    task = resolve_task(workspace_root, task_ref)
    metadata, body = read_markdown_front_matter(source_path)
    payload = dict(metadata)
    payload["body"] = body.rstrip("\n")
    entry = ChangelogEntry.from_dict(payload)
    if entry.task_id != task.id:
        raise LaunchError(
            "Changelog entry task_id mismatch: "
            f"expected {task.id}, got {entry.task_id}."
        )
    assert_changelog_summary_valid(entry.summary, fail_on_warning=True)
    _assert_source_run_belongs_to_task(workspace_root, task.id, entry.source_run_id)
    target = changelog_entry_markdown_path(
        resolve_v2_paths(workspace_root),
        task.id,
        entry.entry_id,
    )
    if target.exists() and not replace:
        raise LaunchError(
            "Changelog entry already exists: "
            f"{entry.entry_id}. Use --replace to overwrite."
        )
    save_changelog_entry(workspace_root, entry)
    return entry


def update_changelog_entry(
    workspace_root: Path,
    task_ref: str,
    entry_id: str,
    *,
    category: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    release_version: str | None = None,
    status: str | None = None,
    audience: str | None = None,
    scopes: tuple[str, ...] | None = None,
    source_run_id: str | None = None,
    source_kind: str | None = None,
) -> ChangelogEntry:
    task = resolve_task(workspace_root, task_ref)
    entries = load_changelog_entries(workspace_root, task.id)
    existing = next((item for item in entries if item.entry_id == entry_id), None)
    if existing is None:
        raise LaunchError(f"Changelog entry not found: {entry_id}")

    if (
        category is None
        and summary is None
        and body is None
        and release_version is None
        and status is None
        and audience is None
        and scopes is None
        and source_run_id is None
        and source_kind is None
    ):
        raise LaunchError("Provide at least one field to update.")

    updated_category = (
        normalize_changelog_category(category)
        if category is not None
        else existing.category
    )
    updated_status = (
        normalize_changelog_status(status) if status is not None else existing.status
    )
    updated_summary = existing.summary if summary is None else summary.strip()
    if summary is not None:
        assert_changelog_summary_valid(updated_summary, fail_on_warning=True)
    updated_scopes = (
        existing.scopes
        if scopes is None
        else tuple(scope.strip() for scope in scopes if scope.strip())
    )
    updated_source_run_id = (
        source_run_id if source_run_id is not None else existing.source_run_id
    )
    _assert_source_run_belongs_to_task(workspace_root, task.id, updated_source_run_id)

    updated = replace(
        existing,
        category=updated_category,
        summary=updated_summary,
        body=existing.body if body is None else body.strip(),
        release_version=(
            release_version if release_version is not None else existing.release_version
        ),
        status=updated_status,
        audience=audience if audience is not None else existing.audience,
        scopes=updated_scopes,
        source_run_id=updated_source_run_id,
        source_kind=source_kind if source_kind is not None else existing.source_kind,
        updated_at=utc_now_iso(),
    )
    save_changelog_entry(workspace_root, updated)
    return updated


def add_many_changelog_entries(
    workspace_root: Path,
    task_ref: str,
    entries: list[dict[str, object]],
    *,
    dry_run: bool = False,
    fail_on_warning: bool = True,
) -> dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    existing_ids = [
        entry.entry_id for entry in load_changelog_entries(workspace_root, task.id)
    ]
    next_ids = list(existing_ids)
    actor = resolve_actor(workspace_root=workspace_root)
    issues: list[dict[str, object]] = []
    planned_entries: list[ChangelogEntry] = []

    for index, raw_entry in enumerate(entries, start=1):
        entry_id = next_project_id("cle", next_ids)
        next_ids.append(entry_id)
        planned = _coerce_batch_entry(
            workspace_root,
            task_id=task.id,
            actor=actor,
            index=index,
            entry_id=entry_id,
            payload=raw_entry,
            issues=issues,
            fail_on_warning=fail_on_warning,
        )
        if planned is not None:
            planned_entries.append(planned)

    if issues:
        raise LaunchError(
            "Changelog batch failed validation.",
            code="VALIDATION_FAILED",
            details={
                "issues": issues,
                "written": False,
            },
            exit_code=7,
        )

    if not dry_run:
        for entry in planned_entries:
            save_changelog_entry(workspace_root, entry)

    return {
        "kind": "changelog_entry_batch",
        "task_id": task.id,
        "entry_count": len(planned_entries),
        "entries": [entry.to_dict() for entry in planned_entries],
        "issues": [],
        "written": not dry_run,
    }


def lint_changelog_entries_for_tasks(
    workspace_root: Path,
    *,
    task_ids: tuple[str, ...],
    version: str | None = None,
    strict: bool = False,
    warn_on_missing_accepted: bool = False,
) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    parsed_entries: list[ChangelogEntry] = []
    checked_files: list[str] = []
    accepted_counts: dict[str, int] = {task_id: 0 for task_id in task_ids}
    paths = resolve_v2_paths(workspace_root)
    workspace = workspace_root.resolve()

    for task_id in task_ids:
        for path in sorted(task_changelog_dir(paths, task_id).glob("cle-*.md")):
            rel_path = (
                path.resolve().relative_to(workspace).as_posix()
                if workspace in path.resolve().parents or path.resolve() == workspace
                else str(path)
            )
            checked_files.append(rel_path)
            try:
                metadata, body = read_markdown_front_matter(path)
            except LaunchError as exc:
                issues.append(
                    _issue(
                        severity="error",
                        path=rel_path,
                        entry_id=path.stem,
                        field="front_matter",
                        message=str(exc),
                    )
                )
                continue

            entry_payload = dict(metadata)
            entry_payload["body"] = body.rstrip("\n")
            try:
                entry = ChangelogEntry.from_dict(entry_payload)
            except LaunchError as exc:
                issues.append(
                    _issue(
                        severity="error",
                        path=rel_path,
                        entry_id=str(entry_payload.get("entry_id") or path.stem),
                        field="schema",
                        message=str(exc),
                    )
                )
                continue

            parsed_entries.append(entry)
            if entry.status == "accepted":
                accepted_counts[task_id] = accepted_counts.get(task_id, 0) + 1
            if entry.task_id != task_id:
                issues.append(
                    _issue(
                        severity="error",
                        path=rel_path,
                        entry_id=entry.entry_id,
                        field="task_id",
                        message=(
                            "Entry task_id does not match containing task directory: "
                            f"{entry.task_id} != {task_id}"
                        ),
                    )
                )
            source_issue = _source_run_issue(workspace_root, entry)
            if source_issue is not None:
                issues.append(
                    _issue(
                        severity="error",
                        path=rel_path,
                        entry_id=entry.entry_id,
                        field="source_run_id",
                        message=source_issue,
                    )
                )
            issues.extend(_summary_issues(entry, rel_path))
            if (
                version is not None
                and entry.release_version is not None
                and entry.release_version != version
            ):
                issues.append(
                    _issue(
                        severity="warning",
                        path=rel_path,
                        entry_id=entry.entry_id,
                        field="release_version",
                        message=(
                            "Entry release_version does not match lint/build version: "
                            f"{entry.release_version} != {version}"
                        ),
                    )
                )

    missing_accepted_task_ids: list[str] = []
    if warn_on_missing_accepted:
        for task_id in task_ids:
            if accepted_counts.get(task_id, 0) > 0:
                continue
            missing_accepted_task_ids.append(task_id)
            issues.append(
                _issue(
                    severity="warning",
                    path="",
                    entry_id="",
                    field="entries",
                    message=f"Done task has no accepted changelog entries: {task_id}",
                )
            )

    errors = sum(1 for item in issues if item.get("severity") == "error")
    warnings = sum(1 for item in issues if item.get("severity") == "warning")
    lint_payload: dict[str, object] = {
        "kind": "changelog_lint",
        "version": version,
        "task_ids": list(task_ids),
        "checked_files": checked_files,
        "entry_count": len(parsed_entries),
        "summary": {
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
        "missing_accepted_task_ids": missing_accepted_task_ids,
        "entries": [entry.to_dict() for entry in parsed_entries],
    }
    if strict and (errors > 0 or warnings > 0):
        raise LaunchError(
            "Changelog lint failed in strict mode.",
            details=lint_payload,
            exit_code=7,
        )
    return lint_payload


def lint_changelog_entries(
    workspace_root: Path,
    *,
    task_ref: str | None = None,
    version: str | None = None,
    strict: bool = False,
) -> dict[str, object]:
    if task_ref is not None and version is not None:
        raise LaunchError("Use either --task or --version, not both.")
    if task_ref is None and version is None:
        raise LaunchError("Provide --task or --version.")
    if task_ref is not None:
        task = resolve_task(workspace_root, task_ref)
        payload = lint_changelog_entries_for_tasks(
            workspace_root,
            task_ids=(task.id,),
            strict=strict,
            warn_on_missing_accepted=False,
        )
        payload["task_id"] = task.id
        return payload

    assert version is not None
    scope = resolve_changelog_version_scope(workspace_root, version=version)
    payload = lint_changelog_entries_for_tasks(
        workspace_root,
        task_ids=scope.task_ids,
        version=version,
        strict=strict,
        warn_on_missing_accepted=True,
    )
    payload["version_scope"] = {
        "version": scope.version,
        "since_version": scope.since_version,
        "since_task_id": scope.since_task_id,
        "until_task_id": scope.until_task_id,
        "range_mode": scope.range_mode,
        "task_ids": list(scope.task_ids),
        "omitted_task_ids": list(scope.omitted_task_ids),
    }
    return payload


def build_changelog_prompt(
    workspace_root: Path,
    task_ref: str,
    *,
    format_name: str = "markdown",
) -> str | dict[str, object]:
    task = resolve_task(workspace_root, task_ref)
    plans = list_plans(workspace_root, task.id)
    accepted_plan = next(
        (plan for plan in plans if plan.plan_version == task.accepted_plan_version),
        plans[-1] if plans else None,
    )
    todos = load_todos(workspace_root, task.id).todos
    completed_todos = [todo for todo in todos if todo.done]
    changes = list_changes(workspace_root, task.id)
    validation_runs = [
        run
        for run in list_runs(workspace_root, task.id)
        if run.run_type == "validation"
    ]
    latest_validation = validation_runs[-1] if validation_runs else None
    implementation_runs = [
        run
        for run in list_runs(workspace_root, task.id)
        if run.run_type == "implementation"
    ]
    latest_implementation = implementation_runs[-1] if implementation_runs else None
    entries = load_changelog_entries(workspace_root, task.id)
    accepted_entries = [entry for entry in entries if entry.status == "accepted"]
    categories = ", ".join(CHANGELOG_CATEGORIES)

    lines: list[str] = [
        f"# Changelog prompt for {task.id} — {task.title}",
        "",
        "Use only the taskledger evidence below. Do not invent changes.",
        "Draft a task-local changelog batch YAML file and apply it atomically.",
        f"Use category values only from: {categories}.",
        "Use status values only from: draft, accepted, rejected.",
        "",
        "## Strict summary rules",
        "",
        (
            "Every summary must be one line and lint-clean under "
            "`taskledger changelog lint`."
        ),
        "Use at most 120 characters when practical; 180 is the hard maximum.",
        "Do not end with a period.",
        "Do not include TODO markers or unchecked checkbox markers.",
        "Avoid raw task IDs unless required.",
        "Start each summary with one of these exact prefixes:",
        "- Added",
        "- Changed",
        "- Deprecated",
        "- Removed",
        "- Fixed",
        "- Secured",
        "- Documented",
        "- Improved",
        "",
        "## Strict-clean examples",
        "",
        "- Changed trace output to taskledger-native references only",
        "- Documented isolated task-ledger semantics in docs and agent guidance",
        "",
        "## Recommended write path",
        "",
        "```bash",
        (
            "taskledger changelog add-many --task TASK_ID "
            "--file /tmp/TASK_ID-changelog.yaml --dry-run"
        ),
        (
            "taskledger changelog add-many --task TASK_ID "
            "--file /tmp/TASK_ID-changelog.yaml"
        ),
        "taskledger changelog lint --task TASK_ID --strict",
        "taskledger changelog list --task TASK_ID",
        "```",
        "",
        "## Suggested add-many YAML skeleton",
        "",
        "```yaml",
        "entries:",
        "  - category: changed",
        "    summary: Changed ...",
        "    body: >-",
        "      ...",
        "    audience: developer",
        "    scopes: [runtime]",
        "```",
        "",
        "## Task",
        "",
        f"- task_id: {task.id}",
        f"- slug: {task.slug}",
        f"- status_stage: {task.status_stage}",
        f"- title: {task.title}",
    ]
    if accepted_plan is not None and accepted_plan.goal:
        lines.append(f"- accepted_goal: {accepted_plan.goal}")
    if accepted_plan is not None and accepted_plan.criteria:
        lines.extend(["", "## Acceptance criteria", ""])
        for criterion in accepted_plan.criteria:
            lines.append(f"- {criterion.id}: {criterion.text}")
    if completed_todos:
        lines.extend(["", "## Implemented todos", ""])
        for todo in completed_todos:
            lines.append(f"- {todo.id}: {todo.text}")
    if changes:
        lines.extend(["", "## Code changes", ""])
        for change in changes:
            if change.kind == "command":
                continue
            lines.append(f"- {change.kind} `{change.path}`: {change.summary}")
    if latest_implementation is not None:
        lines.extend(["", "## Latest implementation summary", ""])
        lines.append(f"- run_id: {latest_implementation.run_id}")
        lines.append(
            f"- result: {latest_implementation.result or latest_implementation.status}"
        )
        if latest_implementation.summary:
            lines.append(f"- summary: {latest_implementation.summary}")
    lines.extend(["", "## Done-work summary from validation", ""])
    if latest_validation is not None and latest_validation.summary:
        lines.append(latest_validation.summary)
    else:
        lines.append("- none")
    if latest_validation is not None:
        lines.extend(["", "## Validation checks and evidence", ""])
        lines.append(f"- run_id: {latest_validation.run_id}")
        lines.append(
            f"- result: {latest_validation.result or latest_validation.status}"
        )
        if latest_validation.summary:
            lines.append(f"- summary: {latest_validation.summary}")
        for check in latest_validation.checks:
            criterion_label = check.criterion_id or check.name
            lines.append(f"- {criterion_label}: {check.status}")
            for evidence in check.evidence:
                lines.append(f"  - evidence: {evidence}")
    lines.extend(["", "## Existing changelog entries", ""])
    lines.append(f"- accepted_entry_count: {len(accepted_entries)}")
    if entries:
        for entry in entries:
            lines.append(
                f"- {entry.entry_id} [{entry.status}] {entry.category}: {entry.summary}"
            )
    else:
        lines.append("- none")
    markdown = "\n".join(lines).rstrip() + "\n"
    normalized_format = format_name.strip().lower()
    if normalized_format in {"markdown", "agent"}:
        return markdown
    if normalized_format == "json":
        return {
            "kind": "changelog_prompt",
            "task_id": task.id,
            "task_title": task.title,
            "categories": list(CHANGELOG_CATEGORIES),
            "statuses": list(CHANGELOG_STATUSES),
            "accepted_entry_count": len(accepted_entries),
            "latest_implementation_summary": (
                latest_implementation.summary
                if latest_implementation is not None
                else None
            ),
            "latest_validation_summary": (
                latest_validation.summary if latest_validation is not None else None
            ),
            "prompt_markdown": markdown,
        }
    raise LaunchError(f"Unsupported changelog prompt format: {format_name}")


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_status_filter(values: tuple[str, ...]) -> frozenset[str]:
    statuses = tuple(values or ("accepted",))
    normalized: list[str] = []
    for status in statuses:
        normalized.append(normalize_changelog_status(status))
    return frozenset(normalized)


def _task_number(task_id: str) -> int:
    match = re.fullmatch(r"task-(\d+)", task_id)
    if match is None:
        raise LaunchError(f"Release ranges require numeric task ids: {task_id}")
    return int(match.group(1))


def _first_task_in_range(workspace_root: Path, until_task_id: str) -> str:
    upper = _task_number(until_task_id)
    candidates = [
        task.id for task in list_tasks(workspace_root) if _task_number(task.id) <= upper
    ]
    if not candidates:
        return until_task_id
    return min(candidates, key=task_numeric_sort_key)


def _assert_source_run_belongs_to_task(
    workspace_root: Path,
    task_id: str,
    source_run_id: str | None,
) -> None:
    if source_run_id is None:
        return
    run_ids = {run.run_id for run in list_runs(workspace_root, task_id)}
    if source_run_id not in run_ids:
        raise LaunchError(
            f"source_run_id {source_run_id} does not belong to task {task_id}."
        )


def _source_run_issue(workspace_root: Path, entry: ChangelogEntry) -> str | None:
    if entry.source_run_id is None:
        return None
    run_ids = {run.run_id for run in list_runs(workspace_root, entry.task_id)}
    if entry.source_run_id in run_ids:
        return None
    return (
        f"source_run_id {entry.source_run_id} does not belong to task {entry.task_id}."
    )


def validate_changelog_summary(summary: str) -> list[dict[str, str]]:
    return _summary_issues_for_text(summary)


def assert_changelog_summary_valid(
    summary: str,
    *,
    fail_on_warning: bool = True,
) -> None:
    issues = validate_changelog_summary(summary)
    blocking = [
        issue
        for issue in issues
        if issue["severity"] == "error"
        or (fail_on_warning and issue["severity"] == "warning")
    ]
    if blocking:
        raise LaunchError(
            "Changelog summary failed validation.",
            code="VALIDATION_FAILED",
            details={"issues": blocking},
            exit_code=7,
        )


def _summary_issues(entry: ChangelogEntry, path: str) -> list[dict[str, object]]:
    issues = _summary_issues_for_text(entry.summary)
    return [
        _issue(
            severity=str(item["severity"]),
            path=path,
            entry_id=entry.entry_id,
            field="summary",
            message=str(item["message"]),
        )
        for item in issues
    ]


def _summary_issues_for_text(summary: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not summary.strip():
        issues.append({"severity": "error", "message": "Summary must not be empty."})
        return issues
    if "\n" in summary:
        issues.append({"severity": "error", "message": "Summary must be one line."})
    if len(summary) > SUMMARY_MAX_CHARS:
        issues.append(
            {
                "severity": "error",
                "message": f"Summary exceeds {SUMMARY_MAX_CHARS} characters.",
            }
        )
    elif len(summary) > SUMMARY_WARN_CHARS:
        issues.append(
            {
                "severity": "warning",
                "message": f"Summary is longer than {SUMMARY_WARN_CHARS} characters.",
            }
        )
    if summary.lstrip().startswith("#"):
        issues.append(
            {"severity": "error", "message": "Summary must not be a Markdown heading."}
        )
    if re.search(r"\bTODO\b|\[ \]", summary):
        issues.append(
            {
                "severity": "error",
                "message": "Summary must not contain unchecked TODO markers.",
            }
        )
    if re.search(r"\btask-\d+\b", summary):
        issues.append(
            {
                "severity": "warning",
                "message": "Summary should avoid raw task IDs unless required.",
            }
        )
    if summary.endswith("."):
        issues.append(
            {
                "severity": "warning",
                "message": (
                    "Summary should avoid a trailing period for bullet style "
                    "consistency."
                ),
            }
        )
    if not summary.startswith(_SUMMARY_ACTION_PREFIXES):
        issues.append(
            {
                "severity": "warning",
                "message": (
                    "Summary should start with an action phrase like Added, Changed, "
                    "Fixed, or Documented."
                ),
            }
        )
    return issues


def _coerce_batch_entry(
    workspace_root: Path,
    *,
    task_id: str,
    actor: ActorRef,
    index: int,
    entry_id: str,
    payload: dict[str, object],
    issues: list[dict[str, object]],
    fail_on_warning: bool,
) -> ChangelogEntry | None:
    category_value = payload.get("category")
    summary_value = payload.get("summary")
    body_value = payload.get("body", "")
    status_value = payload.get("status", "accepted")
    release_version_value = payload.get("release_version")
    audience_value = payload.get("audience")
    scopes_value = payload.get("scopes", ())
    source_run_id_value = payload.get("source_run_id")
    source_kind_value = payload.get("source_kind")

    if not isinstance(category_value, str) or not category_value.strip():
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="category",
                severity="error",
                message="Entry category must be a non-empty string.",
            )
        )
        return None
    if not isinstance(summary_value, str) or not summary_value.strip():
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="summary",
                severity="error",
                message="Entry summary must be a non-empty string.",
            )
        )
        return None
    if not isinstance(body_value, str):
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="body",
                severity="error",
                message="Entry body must be a string.",
            )
        )
        return None
    if not isinstance(status_value, str):
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="status",
                severity="error",
                message="Entry status must be a string.",
            )
        )
        return None

    try:
        category = normalize_changelog_category(category_value)
    except LaunchError as exc:
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="category",
                severity="error",
                message=str(exc),
            )
        )
        return None
    try:
        status = normalize_changelog_status(status_value)
    except LaunchError as exc:
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="status",
                severity="error",
                message=str(exc),
            )
        )
        return None

    if release_version_value is not None and not isinstance(release_version_value, str):
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="release_version",
                severity="error",
                message="release_version must be a string when provided.",
            )
        )
        return None
    if audience_value is not None and not isinstance(audience_value, str):
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="audience",
                severity="error",
                message="audience must be a string when provided.",
            )
        )
        return None
    if source_run_id_value is not None and not isinstance(source_run_id_value, str):
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="source_run_id",
                severity="error",
                message="source_run_id must be a string when provided.",
            )
        )
        return None
    if source_kind_value is not None and not isinstance(source_kind_value, str):
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="source_kind",
                severity="error",
                message="source_kind must be a string when provided.",
            )
        )
        return None
    if scopes_value is None:
        scopes = ()
    elif isinstance(scopes_value, list):
        if not all(isinstance(item, str) for item in scopes_value):
            issues.append(
                _batch_issue(
                    index=index,
                    entry_id=entry_id,
                    field="scopes",
                    severity="error",
                    message="scopes must be a list of strings.",
                )
            )
            return None
        scopes = tuple(item.strip() for item in scopes_value if item.strip())
    else:
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="scopes",
                severity="error",
                message="scopes must be a list of strings.",
            )
        )
        return None

    summary = summary_value.strip()
    summary_issues = validate_changelog_summary(summary)
    for item in summary_issues:
        severity = item.get("severity", "warning")
        if severity == "warning" and not fail_on_warning:
            continue
        issues.append(
            _batch_issue(
                index=index,
                entry_id=entry_id,
                field="summary",
                severity=severity,
                message=str(item.get("message", "")),
            )
        )

    source_run_id = (
        source_run_id_value if isinstance(source_run_id_value, str) else None
    )
    if source_run_id is not None:
        try:
            _assert_source_run_belongs_to_task(workspace_root, task_id, source_run_id)
        except LaunchError as exc:
            issues.append(
                _batch_issue(
                    index=index,
                    entry_id=entry_id,
                    field="source_run_id",
                    severity="error",
                    message=str(exc),
                )
            )

    has_blocking = any(item.get("index") == index for item in issues)
    if has_blocking:
        return None

    return ChangelogEntry(
        entry_id=entry_id,
        task_id=task_id,
        category=category,
        summary=summary,
        body=body_value.strip(),
        status=status,
        release_version=release_version_value,
        audience=audience_value,
        scopes=scopes,
        source_run_id=source_run_id,
        source_kind=source_kind_value if isinstance(source_kind_value, str) else None,
        created_by=actor,
    )


def _batch_issue(
    *,
    index: int,
    entry_id: str,
    field: str,
    severity: str,
    message: str,
) -> dict[str, object]:
    return {
        "index": index,
        "entry_id": entry_id,
        "field": field,
        "severity": severity,
        "message": message,
    }


def _issue(
    *,
    severity: str,
    path: str,
    entry_id: str,
    field: str,
    message: str,
) -> dict[str, object]:
    return {
        "severity": severity,
        "path": path,
        "entry_id": entry_id,
        "field": field,
        "message": message,
    }


__all__ = [
    "ChangelogVersionScope",
    "add_many_changelog_entries",
    "add_changelog_entry",
    "assert_changelog_summary_valid",
    "build_changelog_prompt",
    "import_changelog_entry_file",
    "lint_changelog_entries",
    "lint_changelog_entries_for_tasks",
    "list_changelog_entries",
    "resolve_changelog_version_scope",
    "update_changelog_entry",
    "validate_changelog_summary",
]
