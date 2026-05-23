---
schema_version: 2
id: al_runtime_0035
type: runtime_scenario
title: "Task lifecycle: create through done"
status: accepted
section: runtime_view
order: 10
date: "2026-05-23"
participants: []
trigger: "User or agent runs taskledger task create"
result: ""
body_format: markdown
created_at: "2026-05-23T12:30:49Z"
updated_at: "2026-05-23T12:30:49Z"
---

**Trigger**: User or agent runs `taskledger task create`.

**Flow**:

1. `task create` → TaskRecord persisted in `draft` stage with `task.created` event
2. `plan start` → Lock acquired, planning run started, stage → `planning`
3. `plan propose` → PlanRecord persisted, todos materialized, stage → `plan_review`
4. `plan approve` (user-only) → Stage → `approved`, lock released, run finished
5. `implement start` → Lock acquired, implementation run started, stage → `implementing`
6. `implement log` / `implement finish` → Changes logged, todos completed, stage → `implemented`
7. `validate start` → Lock acquired, validation run started, stage → `validating`
8. `validate check` / `validate finish` → Criteria checked, stage → `done` (or `failed_validation`)

**Result**: Task reaches `done` with all todos complete and all mandatory criteria passed. Events trail the full history.

**Key policy checks**: `can_start_planning`, `plan_propose_decision`, `plan_approve_decision`, implementation requires accepted plan, validation requires finished implementation run.
