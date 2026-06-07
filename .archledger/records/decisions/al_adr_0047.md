---
schema_version: 2
id: al_adr_0047
type: adr
title: JSON indexes as derived rebuildable caches
status: accepted
section: architecture_decisions
order: 20
date: "2026-05-23"
deciders:
  - taskledger maintainers
supersedes: []
related: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:31:02Z"
updated_at: "2026-06-07T11:50:16Z"
source_refs:
  - path: taskledger/storage/task_store.py
    role: implements
    reason: Derived index paths and rebuildable cache contract
test_refs:
  - tests/test_storage_sync.py
---

## Context

Listing tasks, locks, and dependencies requires scanning many front matter files. Need a way to speed up queries without adding a database.

## Decision

Maintain JSON index files under `.taskledger/indexes/` as derived caches. They are rebuilt from canonical records by `taskledger reindex` and checked by `doctor indexes`. They are never the source of truth.

## Consequences

- Positive: Fast list/query operations without parsing all front matter files.
- Positive: Indexes can always be rebuilt from canonical source.
- Negative: Indexes can become stale after manual edits or crashes.
- Negative: `reindex` must be run after out-of-band changes.

## Alternatives considered

- No indexes (always scan files): Simpler but too slow for large projects.
- SQLite index: More robust but adds complexity and dependency.
- In-memory cache: Lost on process restart, not durable.
