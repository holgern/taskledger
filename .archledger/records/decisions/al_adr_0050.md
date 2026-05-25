---
schema_version: 2
id: al_adr_0050
type: adr
title: "Task bundle directory layout"
status: accepted
section: architecture_decisions
order: 50
date: "2026-05-23"
deciders: []
supersedes: []
related: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:31:03Z"
updated_at: "2026-05-23T12:31:03Z"
---

## Context

Need a storage layout that scales to many sidecar collections per task (plans, runs, locks, todos, questions, changes, checks, handoffs, links) while keeping each record individually addressable. Events are stored at ledger level, not per-task, and are opt-in.

## Decision

Use a directory-per-task layout (v2 bundle) under `.taskledger/ledgers/<ledger_ref>/`. Each task gets a directory containing the task record (Markdown) and subdirectories for sidecar collections. JSON indexes are derived caches at the ledger level. Event records are stored in the ledger-level `events/` directory (not per-task) and are only written when `[event_logging] enabled = true`.

## Consequences

- Positive: Each record is a single file — easy to read, edit, and version-control.
- Positive: Sidecar collections are independently addressable.
- Negative: Many small files create directory overhead on very large projects.

## Alternatives considered

- Single JSON index file: Merge conflicts, scalability, not human-readable.
- Database (SQLite): Opaque, harder to inspect and version-control.
