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
- **Action/event logging (default-on)**: Mutations append immutable `TaskEvent` records to the ledger-level `events/` directory under `.taskledger/ledgers/<ledger_ref>/`. Action/event logging is enabled by default; set `[event_logging] enabled = false` to disable new records. Existing records remain readable. Events track who did what, when, and why. Source: `taskledger/storage/events.py`, `taskledger/services/task_events.py`.
- **Exit code taxonomy**: Errors map to stable exit codes (0=success, 1=generic, 2=bad input, 3=workflow rejection, 4=lock conflict, 5=missing, 6=storage, 7=validation failed).
- **Opaque cross-ledger references**: Links and file references remain opaque strings. Taskledger does not interpret archledger IDs, SpecWeave feature paths, or other external system references.
- **Read-model reuse**: `view` and `status` commands consume service-level read models. These presentations are read-only and do not bypass lifecycle services.
