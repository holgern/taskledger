---
schema_version: 2
id: al_glossary_0067
type: glossary_term
title: "Acceptance Criterion"
status: proposed
section: glossary
order: 70
date: "2026-05-23"
term: "Acceptance Criterion"
definition: "A testable condition that gates task completion during validation."
body_format: markdown
created_at: "2026-05-23T12:31:23Z"
updated_at: "2026-05-23T12:31:23Z"
---

A testable condition that gates task completion. Defined in the accepted plan as part of acceptance criteria. During validation, each criterion is checked (pass/fail/warn/not_run). Mandatory criteria must pass for validation to succeed. Persisted as `AcceptanceCriterion` in `taskledger/domain/sidecars.py`.
