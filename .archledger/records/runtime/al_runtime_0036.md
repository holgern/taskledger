---
schema_version: 2
id: al_runtime_0036
type: runtime_scenario
title: "Lock acquisition, heartbeat, and release"
status: accepted
section: runtime_view
order: 20
date: "2026-05-23"
participants: []
trigger: "Service calls _start_run for planning, implementation, or validation"
result: ""
body_format: markdown
created_at: "2026-05-23T12:30:50Z"
updated_at: "2026-05-23T12:30:50Z"
---

**Trigger**: Service calls `_start_run` (e.g., `plan start`, `implement start`, `validate start`).

**Flow**:

1. Check no existing active lock for the task
2. Create `TaskLock` record via `atomic_create_text` (exclusive file creation)
3. Create `TaskRunRecord` with status `running`
4. Append `lock.acquired` and `run.started` events
5. Update task stage to active stage (`planning`/`implementing`/`validating`)
6. Heartbeat updates `last_heartbeat_at` on the lock
7. On finish: run status → `finished`, lock removed, `lock.released` event appended

**Stale lock handling**:

- `lock_is_expired` checks lease expiry
- `lock break` requires explicit user action, records `broken_at`, `broken_by`, `broken_reason`
- `doctor` detects lock/run mismatches

**Key source**: `taskledger/services/tasks.py` (`_start_run`), `taskledger/storage/locks.py`, `taskledger/domain/lock.py`.
