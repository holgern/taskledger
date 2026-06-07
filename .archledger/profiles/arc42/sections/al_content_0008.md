---
schema_version: 2
id: al_content_0008
type: section
section: cross_cutting_concepts
title: Cross-cutting Concepts
order: 80
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

Cross-cutting concerns that span multiple layers:

- **Actor metadata**: Every mutation carries an `ActorRef` (type: agent/user/system, name, role, session, harness). Decisions distinguish user-only actions (approval, waiver) from agent actions.
- **JSON output envelope**: All CLI commands emit a consistent JSON envelope with `ok`, `command`, `result_type`, `result`, `events`, and `warnings` fields when `--json` is passed.
- **YAML front matter serialization**: All canonical records use YAML front matter (`---` delimited) for metadata and Markdown for body. Serialization/deserialization is in `taskledger/storage/frontmatter.py`.
- **Atomic file writes**: All file writes go through `atomic_write_text` (temp file → `os.replace` → directory fsync) to prevent corruption.
- **Opt-in event logging**: When `[event_logging] enabled = true`, mutations append immutable `TaskEvent` records to the ledger-level `events/` directory under `.taskledger/ledgers/<ledger_ref>/`. When disabled (default), no new event records are written; existing records remain readable. Events track who did what, when, and why. Source: `taskledger/storage/events.py`, `taskledger/services/task_events.py`.
- **Exit code taxonomy**: Errors map to stable exit codes (0=success, 1=generic, 2=bad input, 3=workflow rejection, 4=lock conflict, 5=missing, 6=storage, 7=validation failed).
- **Traceability metadata**: BDD examples may bind acceptance-criterion IDs and Archledger IDs. Gherkin export preserves stable task, BDD, criterion, and architecture tags so imported automation results can be matched without parsing prose.
- **Read-model reuse**: `view`, HTML reports/dashboard, and the optional TUI consume service-level read models. These presentations are read-only and do not bypass lifecycle services.
