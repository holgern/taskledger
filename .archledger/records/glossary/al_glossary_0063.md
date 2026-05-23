---
schema_version: 2
id: al_glossary_0063
type: glossary_term
title: "Run"
status: proposed
section: glossary
order: 30
date: "2026-05-23"
term: "Run"
definition: "A record of an active work session (planning, implementation, or validation) paired with a lock."
body_format: markdown
created_at: "2026-05-23T12:31:21Z"
updated_at: "2026-05-23T12:31:21Z"
---

A record of an active work session. Runs have a type (planning/implementation/validation), status (running/paused/finished/passed/failed/blocked/aborted), and are paired with a lock. Created when a stage starts, finished when the stage completes. Persisted as `TaskRunRecord` in `taskledger/domain/run.py`.
