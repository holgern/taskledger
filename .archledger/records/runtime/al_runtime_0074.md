---
schema_version: 2
id: al_runtime_0074
type: runtime_scenario
title: "Branch-scoped ledger selection and fork"
status: accepted
section: runtime_view
order: 50
date: "2026-05-23"
participants: []
trigger: "Developer creates a long-lived Git branch and runs taskledger ledger fork REF"
result: ""
body_format: markdown
created_at: "2026-05-23T19:30:00Z"
updated_at: "2026-05-23T19:30:00Z"
---

**Trigger**: Developer creates a long-lived Git branch and runs `taskledger ledger fork REF`.

**Flow**:

1. `ledger fork feature-a` → Creates a new ledger directory under `.taskledger/ledgers/feature-a/`
2. Commits the updated `taskledger.toml` (with new `ledger_ref`) with the branch work
3. Default commands now read/write only the current ledger under `.taskledger/ledgers/<ledger_ref>/`
4. Tasks in different ledgers are isolated; duplicate logical task IDs are expected across ledgers
5. `ledger adopt --from feature-a task-0030` copies a branch-local task into the current ledger when merging

**Result**: Each long-lived branch has its own isolated task ledger. The active ledger is determined by `ledger_ref` in `taskledger.toml`.

**Key source**: `taskledger/cli_ledger.py`, `taskledger/storage/ledger_config.py`, `taskledger/storage/task_store.py`.
