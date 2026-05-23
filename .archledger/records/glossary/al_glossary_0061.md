---
schema_version: 2
id: al_glossary_0061
type: glossary_term
title: "Task"
status: proposed
section: glossary
order: 10
date: "2026-05-23"
term: "Task"
definition: "The primary unit of work with a managed lifecycle through planning, implementation, and validation stages."
body_format: markdown
created_at: "2026-05-23T12:31:20Z"
updated_at: "2026-05-23T12:31:20Z"
---

The primary unit of work in taskledger. A task has a lifecycle stage (draft → planning → plan_review → approved → implementing → implemented → validating → done), a title, description, and associated sidecar collections (plans, todos, links, requirements, events). Persisted as a `TaskRecord` in `taskledger/domain/task.py`.
