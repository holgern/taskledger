---
schema_version: 2
id: al_runtime_0038
type: runtime_scenario
title: "Doctor integrity check"
status: proposed
section: runtime_view
order: 40
date: "2026-05-23"
participants: []
trigger: "User runs taskledger doctor"
result: ""
body_format: markdown
created_at: "2026-05-23T12:30:52Z"
updated_at: "2026-05-23T12:30:52Z"
---
**Trigger**: User runs `taskledger doctor`.

**Flow**:

1. Resolve project paths and locator
2. Check storage layout version against current version
3. Scan all tasks: verify front matter validity, lock/run consistency, active task state
4. Check index staleness (comparing index contents against canonical records)
5. Check for stale locks (expired leases)
6. Collect structured diagnostics with severity, code, message, and repair hints
7. Report diagnostics to user (human text or JSON)

**Key source**: `taskledger/services/doctor.py`, `taskledger/services/doctor_checks/task_checks.py`, `taskledger/services/doctor_checks/project_scan.py`, `taskledger/services/doctor_checks/migration_checks.py`.
