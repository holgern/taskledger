---
schema_version: 2
id: al_constraint_0017
type: constraint
title: "File-system canonical storage"
status: proposed
section: architecture_constraints
order: 20
date: "2026-05-23"
category: technical
impact: "State is file-based; query performance depends on index rebuilds."
body_format: markdown
created_at: "2026-05-23T12:29:54Z"
updated_at: "2026-05-23T12:29:54Z"
---

All durable state is stored as Markdown files with YAML front matter in `.taskledger/`. This makes state human-readable, diffable in Git, and inspectable without taskledger. The trade-off is that query performance depends on file scanning and index rebuilding rather than a database engine.
