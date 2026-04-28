from __future__ import annotations

import json
from pathlib import Path

from taskledger.domain.models import TaskEvent
from taskledger.errors import LaunchError


def append_event(events_dir: Path, event: TaskEvent) -> Path:
    path = event_log_path(events_dir, event.ts)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
    except OSError as exc:
        raise LaunchError(f"Failed to append event {path}: {exc}") from exc
    return path


def load_events(events_dir: Path) -> list[TaskEvent]:
    if not events_dir.exists():
        return []
    events: list[TaskEvent] = []
    seen_ids: set[str] = set()
    for path in sorted(events_dir.glob("*.ndjson")):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    event = TaskEvent.from_dict(payload)
                    if event.event_id in seen_ids:
                        raise LaunchError(
                            f"Duplicate event id detected: {event.event_id}"
                        )
                    seen_ids.add(event.event_id)
                    events.append(event)
        except (OSError, json.JSONDecodeError) as exc:
            raise LaunchError(f"Failed to read event log {path}: {exc}") from exc
    return sorted(events, key=lambda item: (item.ts, item.event_id))


def load_recent_events(
    events_dir: Path,
    *,
    task_id: str | None = None,
    limit: int = 50,
) -> list[TaskEvent]:
    if limit <= 0 or not events_dir.exists():
        return []
    matches: list[TaskEvent] = []
    for path in sorted(events_dir.glob("*.ndjson"), reverse=True):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise LaunchError(f"Failed to read event log {path}: {exc}") from exc
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LaunchError(f"Failed to read event log {path}: {exc}") from exc
            if not isinstance(payload, dict):
                continue
            event = TaskEvent.from_dict(payload)
            if task_id is not None and event.task_id != task_id:
                continue
            matches.append(event)
            if len(matches) >= limit:
                return list(reversed(matches))
    return list(reversed(matches))


def next_event_id(events_dir: Path, timestamp: str) -> str:
    sequence = len(load_events(events_dir)) + 1
    normalized = (
        timestamp.replace(":", "")
        .replace("-", "")
        .replace("+00:00", "Z")
        .replace(".", "")
    )
    return f"evt-{normalized}-{sequence:06d}"


def event_log_path(events_dir: Path, timestamp: str) -> Path:
    return events_dir / f"{timestamp[:10]}.ndjson"


__all__ = [
    "append_event",
    "event_log_path",
    "load_events",
    "load_recent_events",
    "next_event_id",
]
