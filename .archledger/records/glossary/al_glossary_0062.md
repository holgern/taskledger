---
schema_version: 2
id: al_glossary_0062
type: glossary_term
title: "Plan"
status: proposed
section: glossary
order: 20
date: "2026-05-23"
term: "Plan"
definition: "A proposed implementation plan with acceptance criteria that gates implementation start."
body_format: markdown
created_at: "2026-05-23T12:31:21Z"
updated_at: "2026-05-23T12:31:21Z"
---

A proposed implementation plan for a task. Has status (draft → proposed → accepted/superseded/rejected), acceptance criteria, and a body describing the approach. When accepted, todos are materialized from the plan. Persisted as `PlanRecord` in `taskledger/domain/plan.py`.
