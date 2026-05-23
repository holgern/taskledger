---
schema_version: 2
id: al_concept_0043
type: concept
title: "Atomic file writes"
status: proposed
section: cross_cutting_concepts
order: 40
date: "2026-05-23"
applies_to: []
body_format: markdown
created_at: "2026-05-23T12:31:01Z"
updated_at: "2026-05-23T12:31:01Z"
---

All file writes go through `atomic_write_text` (temp file → flush/fsync → `os.replace` → directory fsync) or `atomic_create_text` (`O_CREAT | O_EXCL` for lock files). This prevents partial writes on crash. Test environments can disable fsync via `TASKLEDGER_TEST_FAST_IO=1` for speed. Source: `taskledger/storage/atomic.py`.
