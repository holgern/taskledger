from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from taskledger.domain.models import (
    CHANGELOG_CATEGORY_HEADINGS,
    CHANGELOG_RENDER_ORDER,
    ChangelogEntry,
)
from taskledger.errors import LaunchError
from taskledger.services.changelog_entries import (
    lint_changelog_entries_for_tasks,
    resolve_changelog_version_scope,
)
from taskledger.services.releases import build_changelog_context
from taskledger.storage.task_store import (
    resolve_task,
    task_numeric_sort_key,
)


def build_changelog_section(  # noqa: C901
    workspace_root: Path,
    *,
    version: str,
    release_date: str,
    since_version: str | None = None,
    since_task: str | None = None,
    from_task: str | None = None,
    until_task: str | None = None,
    include_draft: bool = False,
    strict: bool = True,
) -> dict[str, object]:
    _validate_release_date(release_date)
    selectors = [
        since_version is not None,
        since_task is not None,
        from_task is not None,
    ]
    release_scope = None
    try:
        release_scope = resolve_changelog_version_scope(workspace_root, version=version)
    except LaunchError:
        release_scope = None

    if release_scope is not None:
        if any(selectors) or until_task is not None:
            raise LaunchError(
                "Release version is already tagged; do not pass manual range selectors."
            )
        since_version = release_scope.since_version
        until_task = release_scope.until_task_id
        if since_version is None:
            from_task = release_scope.task_ids[0] if release_scope.task_ids else None
    else:
        if sum(selectors) != 1:
            raise LaunchError(
                "Provide exactly one of --since, --since-task, or --from-task."
            )
        if until_task is None:
            raise LaunchError("Manual range build requires --until-task.")

    if until_task is None:
        raise LaunchError("Build range is missing an upper task boundary.")
    boundary_task = resolve_task(workspace_root, until_task)
    if strict and boundary_task.status_stage != "done":
        raise LaunchError(
            f"Release boundary task must be done: {boundary_task.id} is "
            f"{boundary_task.status_stage}."
        )

    context = cast(
        dict[str, object],
        build_changelog_context(
            workspace_root,
            version=version,
            since_version=since_version,
            since_task=since_task,
            from_task=from_task,
            until_task=until_task,
            format_name="json",
        ),
    )
    task_ids = tuple(
        str(item.get("task_id") or "")
        for item in _dict_list(context.get("tasks"))
        if item.get("task_id")
    )
    omitted_task_ids = tuple(
        str(item.get("task_id") or "")
        for item in _dict_list(context.get("omitted_tasks"))
        if item.get("task_id")
    )

    lint_payload = lint_changelog_entries_for_tasks(
        workspace_root,
        task_ids=task_ids,
        version=version,
        strict=False,
        warn_on_missing_accepted=True,
    )
    lint_issues = _dict_list(lint_payload.get("issues"))
    lint_errors = [issue for issue in lint_issues if issue.get("severity") == "error"]
    if lint_errors and strict:
        raise LaunchError(
            "Changelog build blocked by invalid changelog entry files.",
            details={
                "kind": "changelog_build",
                "version": version,
                "errors": lint_errors,
            },
            exit_code=7,
        )

    entries = [
        ChangelogEntry.from_dict(item)
        for item in _dict_list(lint_payload.get("entries"))
    ]
    accepted_entries = [entry for entry in entries if entry.status == "accepted"]
    if strict and not accepted_entries:
        raise LaunchError(
            "Changelog build requires at least one accepted changelog entry.",
            details={
                "kind": "changelog_build",
                "version": version,
                "task_ids": list(task_ids),
                "hint": [
                    "taskledger changelog prompt --task TASK_ID",
                    "taskledger changelog add-many --task TASK_ID "
                    "--file /tmp/TASK_ID-changelog.yaml",
                ],
            },
            exit_code=7,
        )

    included_entries: list[ChangelogEntry] = []
    warnings: list[str] = []
    for entry in entries:
        if entry.status == "rejected":
            continue
        if entry.status == "draft" and not include_draft:
            continue
        included_entries.append(entry)
        if entry.release_version is not None and entry.release_version != version:
            warnings.append(
                f"{entry.entry_id} has release_version "
                f"{entry.release_version}, expected {version}."
            )
        if entry.category == "internal":
            warnings.append(
                f"{entry.entry_id} uses category 'internal'; verify this is intended."
            )

    if not included_entries:
        warnings.append("No changelog entries were selected for this build.")
    for issue in lint_issues:
        if issue.get("severity") != "warning":
            continue
        message = issue.get("message")
        if isinstance(message, str):
            warnings.append(message)

    entries_by_category: dict[str, list[ChangelogEntry]] = {
        category: [] for category in CHANGELOG_RENDER_ORDER
    }
    for entry in sorted(
        included_entries,
        key=lambda item: (task_numeric_sort_key(item.task_id), item.entry_id),
    ):
        entries_by_category[entry.category].append(entry)

    category_counts: dict[str, int] = {}
    for category in CHANGELOG_RENDER_ORDER:
        count = len(entries_by_category[category])
        if count:
            category_counts[category] = count

    section = _render_section(
        version=version,
        release_date=release_date,
        entries_by_category=entries_by_category,
    )
    return {
        "kind": "changelog_build",
        "version": version,
        "release_date": release_date,
        "since_version": context.get("since_version"),
        "since_task_id": context.get("since_task_id"),
        "until_task_id": context.get("until_task_id"),
        "range_mode": context.get("range_mode"),
        "task_ids": list(task_ids),
        "omitted_task_ids": list(omitted_task_ids),
        "task_count": len(task_ids),
        "entry_count": len(included_entries),
        "accepted_entry_count": len(accepted_entries),
        "categories": category_counts,
        "warnings": _dedupe(warnings),
        "section": section,
        "entries": [entry.to_dict() for entry in included_entries],
    }


def render_changelog_section(payload: dict[str, object]) -> str:
    section = payload.get("section")
    if isinstance(section, str) and section.strip():
        return section.rstrip() + "\n"
    version = str(payload.get("version") or "").strip()
    release_date = str(payload.get("release_date") or "").strip()
    if not version or not release_date:
        raise LaunchError(
            "Cannot render changelog section without version and release_date."
        )
    entries_by_category: dict[str, list[ChangelogEntry]] = {
        category: [] for category in CHANGELOG_RENDER_ORDER
    }
    for item in _dict_list(payload.get("entries")):
        entry = ChangelogEntry.from_dict(item)
        entries_by_category[entry.category].append(entry)
    return _render_section(
        version=version,
        release_date=release_date,
        entries_by_category=entries_by_category,
    )


def update_changelog_file(
    target_path: Path,
    *,
    section: str,
    version: str,
    replace: bool = False,
) -> dict[str, object]:
    normalized_section = section.strip()
    if not normalized_section:
        raise LaunchError("Rendered changelog section is empty.")
    heading_pattern = re.compile(rf"(?m)^##\s+v{re.escape(version)}\b[^\n]*$")
    created = False
    replaced = False
    target_text = ""
    if target_path.exists():
        target_text = target_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    else:
        created = True

    if created:
        updated = f"# Changelog\n\n{normalized_section}\n"
        _write_text(target_path, updated)
        return {
            "written": True,
            "created": True,
            "replaced": False,
            "path": str(target_path),
        }

    match = heading_pattern.search(target_text)
    if match is not None:
        if not replace:
            raise LaunchError(
                f"Changelog section for v{version} already exists. Use --replace."
            )
        section_start = match.start()
        following = target_text[match.end() :]
        next_heading = re.search(r"(?m)^##\s+", following)
        section_end = (
            match.end() + next_heading.start()
            if next_heading is not None
            else len(target_text)
        )
        before = target_text[:section_start].rstrip("\n")
        after = target_text[section_end:].lstrip("\n")
        updated = before + "\n\n" + normalized_section + "\n"
        if after:
            updated += "\n" + after
        replaced = True
        _write_text(target_path, updated)
        return {
            "written": True,
            "created": False,
            "replaced": replaced,
            "path": str(target_path),
        }

    title_match = re.search(r"(?m)^#\s+Changelog\s*$", target_text)
    if title_match is None:
        updated = (
            "# Changelog\n\n" + normalized_section + "\n\n" + target_text.lstrip("\n")
        )
        _write_text(target_path, updated)
        return {
            "written": True,
            "created": False,
            "replaced": False,
            "path": str(target_path),
        }

    unreleased_match = re.search(r"(?m)^##\s+Unreleased\b[^\n]*$", target_text)
    insert_at = title_match.end()
    if unreleased_match is not None and unreleased_match.start() > title_match.start():
        tail = target_text[unreleased_match.end() :]
        next_heading = re.search(r"(?m)^##\s+", tail)
        insert_at = (
            unreleased_match.end() + next_heading.start()
            if next_heading is not None
            else len(target_text)
        )
    before = target_text[:insert_at].rstrip("\n")
    after = target_text[insert_at:].lstrip("\n")
    updated = before + "\n\n" + normalized_section + "\n"
    if after:
        updated += "\n" + after
    _write_text(target_path, updated)
    return {
        "written": True,
        "created": False,
        "replaced": False,
        "path": str(target_path),
    }


def _render_section(
    *,
    version: str,
    release_date: str,
    entries_by_category: dict[str, list[ChangelogEntry]],
) -> str:
    lines = [f"## v{version} - {release_date}", ""]
    for category in CHANGELOG_RENDER_ORDER:
        entries = entries_by_category.get(category) or []
        if not entries:
            continue
        heading = CHANGELOG_CATEGORY_HEADINGS[category]
        lines.append(f"### {heading}")
        lines.append("")
        for entry in entries:
            lines.append(f"- {entry.summary}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate_release_date(value: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise LaunchError("--release-date must use YYYY-MM-DD format.")


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8")


__all__ = [
    "build_changelog_section",
    "render_changelog_section",
    "update_changelog_file",
]
