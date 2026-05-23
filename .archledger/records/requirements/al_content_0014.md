---
schema_version: 2
id: al_content_0014
type: requirement
title: "Explicit lifecycle gates with user approval"
status: proposed
section: introduction_and_goals
order: 20
date: "2026-05-23"
source: ""
priority: must
stakeholders: []
quality_goals: []
body_format: markdown
created_at: "2026-05-23T12:29:53Z"
updated_at: "2026-05-23T12:29:53Z"
---

## Requirement

Transitions between task lifecycle stages must pass through policy gates. Plan approval is a user-only decision. Implementation requires an accepted plan. Validation requires a finished implementation.

## Rationale

- Without gates, agents could skip review and ship unreviewed code. The lifecycle machine in `taskledger/domain/states.py` and policy decisions in `taskledger/domain/policies.py` enforce this contract.
- Evidence: `taskledger/domain/states.py` (`ALLOWED_STAGE_TRANSITIONS`), `taskledger/domain/policies.py` (`Decision`, `can_start_planning`, `plan_approve_decision`).
