---
schema_version: 2
id: al_strategy_0025
type: strategy_item
title: "Markdown/YAML front matter as canonical records"
status: proposed
section: solution_strategy
order: 20
date: "2026-05-23"
drivers: []
constraints: []
related_adrs: []
body_format: markdown
created_at: "2026-05-23T12:30:14Z"
updated_at: "2026-05-23T12:30:14Z"
---

## Strategy

Each persistent record (task, plan, run, lock, handoff, event, etc.) is stored as a `.md` file with YAML front matter for structured metadata and a Markdown body for free-form content. This format is human-readable, Git-diffable, and editable without taskledger. The front matter serialization is handled by `taskledger/storage/frontmatter.py`.

## Trade-offs

- Slower to parse than JSON or SQLite for large datasets.
- State is transparent and version-controllable — a core design goal.
- Schema evolution requires careful front matter validation (`_require_contract`, `_string_value`, etc.).
