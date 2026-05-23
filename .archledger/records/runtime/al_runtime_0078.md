---
schema_version: 2
id: al_runtime_0078
type: runtime_scenario
title: "Worker pipeline guided handoff"
status: accepted
section: runtime_view
order: 90
date: "2026-05-23"
participants: []
trigger: "Agent runs taskledger next-action and receives worker_pipeline.next_step in the response"
result: ""
body_format: markdown
created_at: "2026-05-23T19:30:00Z"
updated_at: "2026-05-23T19:30:00Z"
---

**Trigger**: Agent runs `taskledger next-action` and receives `worker_pipeline.next_step` in the response.

**Flow**:

1. `next-action` → Returns `worker_pipeline.next_step` with `step_id`, `context_command`, and `handoff_command` hints
2. `pipeline show` → Displays the configured worker pipeline steps and their mapping to lifecycle stages
3. `context --worker spec-reviewer` → Renders a worker-specific context for the spec reviewer step
4. `handoff create --worker code-reviewer` → Creates a handoff with mode and context derived from the worker step configuration
5. Plan todos may be tagged with `worker_step` to associate implementation steps with specific pipeline workers
6. `plan template --with-worker-pipeline` → Generates plan template with worker-tagged todo sections

**Result**: Worker pipeline provides an advisory overlay that guides fresh-context handoffs through sequential worker steps (spec-reviewer, implementer, code-reviewer). It does not add new lifecycle gates — the task lifecycle remains the authoritative workflow.

**Key source**: `taskledger/services/worker_pipeline.py`, `taskledger/cli_pipeline.py`, `taskledger/services/handoff.py`.
