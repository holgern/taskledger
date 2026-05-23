---
schema_version: 2
id: al_glossary_0065
type: glossary_term
title: "Handoff"
status: proposed
section: glossary
order: 50
date: "2026-05-23"
term: "Handoff"
definition: "A context transfer record enabling a different actor to continue work from where the previous actor left off."
body_format: markdown
created_at: "2026-05-23T12:31:22Z"
updated_at: "2026-05-23T12:31:22Z"
---

A context transfer record that allows a different actor or process to continue work. Contains a generated context body (task state, plan, todos, questions, lock info) and a lock policy (none/retain/release/transfer). Lifecycle: open → claimed → closed/cancelled. Persisted as `TaskHandoffRecord` in `taskledger/domain/handoff.py`.
