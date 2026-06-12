from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from taskledger.domain._model_utils import (
    _int_value,
    _optional_string,
    _require_contract,
    _string_tuple,
    _string_value,
)
from taskledger.domain.actor import ActorRef
from taskledger.domain.states import (
    TASKLEDGER_SCHEMA_VERSION,
    TASKLEDGER_V2_FILE_VERSION,
)
from taskledger.errors import LaunchError
from taskledger.timeutils import utc_now_iso

ChangelogCategory = Literal[
    "added",
    "changed",
    "deprecated",
    "removed",
    "fixed",
    "security",
    "documentation",
    "quality",
    "internal",
]
ChangelogEntryStatus = Literal["draft", "accepted", "rejected"]

CHANGELOG_CATEGORIES: tuple[str, ...] = (
    "added",
    "changed",
    "deprecated",
    "removed",
    "fixed",
    "security",
    "documentation",
    "quality",
    "internal",
)
CHANGELOG_CATEGORY_HEADINGS: dict[str, str] = {
    "added": "Added",
    "changed": "Changed",
    "deprecated": "Deprecated",
    "removed": "Removed",
    "fixed": "Fixed",
    "security": "Security",
    "documentation": "Documentation",
    "quality": "Quality",
    "internal": "Internal",
}
CHANGELOG_STATUSES: tuple[str, ...] = ("draft", "accepted", "rejected")
CHANGELOG_RENDER_ORDER: tuple[str, ...] = CHANGELOG_CATEGORIES


def normalize_changelog_category(value: str) -> ChangelogCategory:
    normalized = value.strip().lower()
    if normalized not in CHANGELOG_CATEGORIES:
        raise LaunchError(f"Unknown changelog category: {value}")
    return cast(ChangelogCategory, normalized)


def normalize_changelog_status(value: str) -> ChangelogEntryStatus:
    normalized = value.strip().lower()
    if normalized not in CHANGELOG_STATUSES:
        raise LaunchError(f"Unsupported changelog status: {value}")
    return cast(ChangelogEntryStatus, normalized)


@dataclass(slots=True, frozen=True)
class ChangelogEntry:
    entry_id: str
    task_id: str
    category: ChangelogCategory
    summary: str
    body: str = ""
    status: ChangelogEntryStatus = "accepted"
    release_version: str | None = None
    audience: str | None = None
    scopes: tuple[str, ...] = ()
    source_run_id: str | None = None
    source_kind: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    created_by: ActorRef = field(default_factory=ActorRef)
    file_version: str = TASKLEDGER_V2_FILE_VERSION
    schema_version: int = TASKLEDGER_SCHEMA_VERSION
    object_type: str = "changelog_entry"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "file_version": self.file_version,
            "entry_id": self.entry_id,
            "task_id": self.task_id,
            "category": self.category,
            "summary": self.summary,
            "body": self.body,
            "status": self.status,
            "release_version": self.release_version,
            "audience": self.audience,
            "scopes": list(self.scopes),
            "source_run_id": self.source_run_id,
            "source_kind": self.source_kind,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ChangelogEntry:
        _require_contract(data, expected_object_type="changelog_entry")
        category = normalize_changelog_category(_string_value(data, "category"))
        status = normalize_changelog_status(
            _optional_string(data.get("status")) or "accepted"
        )
        return cls(
            entry_id=_string_value(data, "entry_id"),
            task_id=_string_value(data, "task_id"),
            category=category,
            summary=_string_value(data, "summary"),
            body=_optional_string(data.get("body")) or "",
            status=status,
            release_version=_optional_string(data.get("release_version")),
            audience=_optional_string(data.get("audience")),
            scopes=_string_tuple(data.get("scopes")),
            source_run_id=_optional_string(data.get("source_run_id")),
            source_kind=_optional_string(data.get("source_kind")),
            created_at=_optional_string(data.get("created_at")) or utc_now_iso(),
            updated_at=_optional_string(data.get("updated_at")) or utc_now_iso(),
            created_by=ActorRef.from_dict(data.get("created_by")),
            file_version=_optional_string(data.get("file_version"))
            or TASKLEDGER_V2_FILE_VERSION,
            schema_version=_int_value(data, "schema_version"),
            object_type=_string_value(data, "object_type"),
        )
