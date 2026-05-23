---
schema_version: 2
id: al_glossary_0070
type: glossary_term
title: "Stage"
status: proposed
section: glossary
order: 100
date: "2026-05-23"
term: "Stage"
definition: "A position in the task lifecycle state machine (draft, planning, plan_review, approved, etc.)."
body_format: markdown
created_at: "2026-05-23T12:31:25Z"
updated_at: "2026-05-23T12:31:25Z"
---

A position in the task lifecycle: draft, planning, plan_review, approved, implementing, implemented, validating, done, failed_validation, cancelled. Active stages (planning, implementing, validating) require a matching running run and a visible lock. Transitions are governed by `ALLOWED_STAGE_TRANSITIONS` in `taskledger/domain/states.py`.
