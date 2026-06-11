---
schema_version: 2
id: al_concept_0044
type: concept
title: "Append-only event log"
status: proposed
section: cross_cutting_concepts
order: 50
date: "2026-05-23"
applies_to: []
body_format: markdown
created_at: "2026-05-23T12:31:01Z"
updated_at: "2026-05-23T12:31:01Z"
---

Mutations append an immutable `TaskEvent` record to the ledger-level `events/` directory under `.taskledger/ledgers/<ledger_ref>/`. Action/event logging is enabled by default; set `[event_logging] enabled = false` in `taskledger.toml` to disable new event records. Existing records remain readable regardless of the setting. Events are never modified or deleted. Each event has a deterministic ID, name (e.g., `task.created`, `plan.approved`, `lock.acquired`, `validation.check.logged`, `code_review.recorded`), timestamp, and actor metadata. Events support audit trails, monitor activity, handoff context, and `task transcript` output. Duplicate event detection prevents re-appending on retry. Source: `taskledger/storage/events.py`, `taskledger/services/task_events.py`, `taskledger/domain/event.py`.
