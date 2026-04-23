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
    for path in sorted(events_dir.glob("*.ndjson")):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    events.append(TaskEvent.from_dict(payload))
        except (OSError, json.JSONDecodeError) as exc:
            raise LaunchError(f"Failed to read event log {path}: {exc}") from exc
    return events


def event_log_path(events_dir: Path, timestamp: str) -> Path:
    return events_dir / f"{timestamp[:10]}.ndjson"
