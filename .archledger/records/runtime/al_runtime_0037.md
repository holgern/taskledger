---
schema_version: 2
id: al_runtime_0037
type: runtime_scenario
title: "Handoff creation and claiming"
status: proposed
section: runtime_view
order: 30
date: "2026-05-23"
participants: []
trigger: "Worker runs taskledger handoff create"
result: ""
body_format: markdown
created_at: "2026-05-23T12:30:50Z"
updated_at: "2026-05-23T12:30:50Z"
---
**Trigger**: Worker runs `taskledger handoff create`.

**Flow**:

1. Generate context body: task state, accepted plan, todos, questions, lock/run status, implementation summary, validation status
2. Create `TaskHandoffRecord` with mode (planning/implementation/validation/review/full), lock policy (none/retain/release/transfer), intended actor and harness
3. Persist handoff record, append `handoff.created` event
4. Another worker runs `handoff claim` → status → `claimed`, optional lock transfer
5. Worker completes work, runs `handoff close` → status → `closed`

**Key source**: `taskledger/services/handoff.py` (context generation), `taskledger/services/handoff_lifecycle.py` (claim/close/transfer), `taskledger/services/worker_context.py` (context assembly).
