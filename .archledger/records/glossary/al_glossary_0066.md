---
schema_version: 2
id: al_glossary_0066
type: glossary_term
title: "Todo"
status: proposed
section: glossary
order: 60
date: "2026-05-23"
term: "Todo"
definition: "A concrete implementation step materialized from the accepted plan; gates implementation completion."
body_format: markdown
created_at: "2026-05-23T12:31:23Z"
updated_at: "2026-05-23T12:31:23Z"
---

A concrete implementation step within a task. Todos are materialized from accepted plans and gate implementation completion (all mandatory todos must be done to finish implementation). Status: open/active/done/blocked/skipped. Persisted as `TaskTodo` in sidecar collections via `taskledger/domain/sidecars.py`.
