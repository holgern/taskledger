---
schema_version: 2
id: al_quality_0052
type: quality_requirement
title: "Data integrity: atomic writes and front matter validation"
status: proposed
section: quality_requirements
order: 10
date: "2026-05-23"
category: reliability
source: ""
measure: ""
scenarios: []
body_format: markdown
created_at: "2026-05-23T12:31:17Z"
updated_at: "2026-05-23T12:31:17Z"
---

## Requirement

No partial or corrupt records should ever be readable. Atomic writes (`os.replace`) prevent partial files. Front matter validation (`_require_contract`, `_string_value`, type checks) rejects malformed records on read.

## Measurement

- `test_atomic_fast_io.py` covers atomic write and create semantics.
- `test_storage_bundle_layout.py` covers front matter validation and corruption detection.
- `doctor` checks detect invalid front matter.
