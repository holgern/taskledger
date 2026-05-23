---
schema_version: 2
id: al_strategy_0028
type: strategy_item
title: "Atomic file writes for durability"
status: proposed
section: solution_strategy
order: 50
date: "2026-05-23"
drivers: []
constraints: []
related_adrs: []
body_format: markdown
created_at: "2026-05-23T12:30:15Z"
updated_at: "2026-05-23T12:30:15Z"
---

## Strategy

All file writes go through `atomic_write_text` in `taskledger/storage/atomic.py`: write to a temp file in the target directory, flush + fsync, then `os.replace` for atomic rename. Directory fsync follows. Lock creation uses `atomic_create_text` with `O_CREAT | O_EXCL` for exclusive creation. These patterns prevent partial or corrupt writes on crash.

## Trade-offs

- Slightly slower than direct writes due to temp file + fsync overhead.
- Can be disabled for testing via `TASKLEDGER_TEST_FAST_IO` environment variable.
- Guarantees that readers always see complete, valid files.
