---
schema_version: 2
id: al_strategy_0026
type: strategy_item
title: "JSON indexes as rebuildable derived caches"
status: proposed
section: solution_strategy
order: 30
date: "2026-05-23"
drivers: []
constraints: []
related_adrs: []
body_format: markdown
created_at: "2026-05-23T12:30:14Z"
updated_at: "2026-05-23T12:30:14Z"
---

## Strategy

JSON index files under `.taskledger/indexes/` are derived caches rebuilt from canonical Markdown records by `taskledger reindex`. They speed up list and query operations but are never authoritative. `doctor indexes` checks for staleness.

## Trade-offs

- Avoids the complexity of a query engine on front matter files.
- Indexes can become stale if writes bypass taskledger (e.g., manual edits). `doctor` and `reindex` address this.
- Index files have no version metadata — they are plain JSON arrays.
