---
schema_version: 2
id: al_content_0006
type: section
section: runtime_view
title: Runtime View
order: 60
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

The runtime view traces the main operational scenarios through the system:

1. **Task lifecycle** — A task is created in `draft`, moves to `planning` (lock acquired, run started), then `plan_review` after a plan is proposed. The user approves → `approved`. Implementation starts → `implementing`, finishes → `implemented`. Validation starts → `validating`, passes → `done`.
2. **Lock lifecycle** — Starting a stage (planning/implementation/validation) acquires a lock and creates a run. Locks have lease timers and heartbeats. Stale locks require explicit break flow with audit trail.
3. **Handoff flow** — A worker creates a handoff with generated context (task state, plan, todos, questions, lock info). Another worker claims it, optionally transferring the lock. The handoff is closed when the receiving worker completes.
4. **Doctor checks** — Inspects lock/run consistency, front matter integrity, index staleness, and storage layout version. Reports diagnostics with severity, code, and repair hints.
5. **BDD evidence flow** — BDD examples link to acceptance criteria and optional Archledger records, export tagged Gherkin, and import Cucumber/JUnit results into durable reports and validation evidence.
6. **Code-review evidence** — A reviewer records append-only review evidence against an implementation run, handoff, worker step, working tree, or commit. This is evidence attached to the task, not a new lifecycle stage.
