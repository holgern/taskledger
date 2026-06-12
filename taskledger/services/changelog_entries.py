from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from taskledger.domain.models import (
    CHANGELOG_CATEGORIES,
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
) -> ChangelogEntry:
    task = resolve_task(workspace_root, task_ref)
    normalized_category = normalize_changelog_category(category)
    normalized_status = normalize_changelog_status(status)
    cleaned_summary = summary.strip()
    if not cleaned_summary:
        raise LaunchError("Changelog summary must not be empty.")
    _assert_summary_valid(cleaned_summary)
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
    _assert_summary_valid(entry.summary)
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
) -> str:
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
    entries = load_changelog_entries(workspace_root, task.id)
    categories = ", ".join(CHANGELOG_CATEGORIES)

    lines: list[str] = [
        f"# Changelog prompt for {task.id} — {task.title}",
        "",
        "Use only the taskledger evidence below. Do not invent changes.",
        "Write one YAML-frontmatter Markdown file per changelog bullet.",
        f"Use category values only from: {categories}.",
        (
            "Prefer user-visible summary wording. Do not mention task ids unless"
            " necessary."
        ),
        "",
        "## Output contract",
        "",
        "Each file must include YAML front matter with:",
        "- schema_version",
        "- object_type: changelog_entry",
        "- file_version",
        "- entry_id",
        "- task_id",
        "- category",
        "- status",
        "- summary",
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
    if entries:
        for entry in entries:
            lines.append(
                f"- {entry.entry_id} [{entry.status}] {entry.category}: {entry.summary}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


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


def _assert_summary_valid(summary: str) -> None:
    for issue in _summary_issues_for_text(summary):
        if issue["severity"] == "error":
            raise LaunchError(str(issue["message"]))


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
    "add_changelog_entry",
    "build_changelog_prompt",
    "import_changelog_entry_file",
    "lint_changelog_entries",
    "lint_changelog_entries_for_tasks",
    "list_changelog_entries",
    "resolve_changelog_version_scope",
]
