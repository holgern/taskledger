---
schema_version: 2
id: al_adr_0048
type: adr
title: "Explicit lifecycle gates with policy decisions"
status: proposed
section: architecture_decisions
order: 30
date: "2026-05-23"
deciders: []
supersedes: []
related: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:31:02Z"
updated_at: "2026-05-23T12:31:02Z"
---

## Context

Without lifecycle gates, agents could skip review and implement without approval. Need enforceable transitions between task stages.

## Decision

Implement lifecycle gates as pure policy functions in `taskledger/domain/policies.py`. Each gate function takes a `PolicyContext` (task, lock, run) and returns a `Decision` (allowed, code, message, exit_code). The state machine in `states.py` defines `ALLOWED_STAGE_TRANSITIONS`. Services call policies before mutating state.

## Consequences

- Positive: Gate logic is fully testable without I/O setup.
- Positive: User-only actions (approval, waivers) are enforced at the policy level.
- Negative: Services must gather full context before calling policies.

## Alternatives considered

- Free-form state changes: Rejected — agents could bypass review.
- Database triggers: Rejected — adds database dependency and complexity.
- CLI-only validation: Rejected — API and programmatic users would bypass gates.
