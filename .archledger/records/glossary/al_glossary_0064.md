---
schema_version: 2
id: al_glossary_0064
type: glossary_term
title: "Lock"
status: proposed
section: glossary
order: 40
date: "2026-05-23"
term: "Lock"
definition: "A concurrency control mechanism preventing simultaneous actors on the same task stage."
body_format: markdown
created_at: "2026-05-23T12:31:22Z"
updated_at: "2026-05-23T12:31:22Z"
---

A concurrency control mechanism that prevents multiple actors from working on the same task stage simultaneously. Locks have a lease timer, holder (`ActorRef`), and optional transfer history. Stale locks require explicit break flow with audit record. Persisted as `TaskLock` in `taskledger/domain/lock.py`.
