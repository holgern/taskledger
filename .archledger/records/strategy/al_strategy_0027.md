---
schema_version: 2
id: al_strategy_0027
type: strategy_item
title: "Policy-based lifecycle gate decisions"
status: proposed
section: solution_strategy
order: 40
date: "2026-05-23"
drivers: []
constraints: []
related_adrs: []
body_format: markdown
created_at: "2026-05-23T12:30:15Z"
updated_at: "2026-05-23T12:30:15Z"
---

## Strategy

All lifecycle transitions are validated through pure functions in `taskledger/domain/policies.py` that return `Decision` objects (`allowed`, `code`, `message`, `exit_code`). Policies have no I/O — they receive `PolicyContext` (task, lock, run) and return a decision. This makes gate logic fully testable without file system setup.

## Trade-offs

- Policy functions must receive all context explicitly (no lazy loading from storage).
- Very testable: `test_domain_policies.py` and `test_lifecycle_policies.py` cover the full decision surface.
- Services must gather the right context before calling policies.
