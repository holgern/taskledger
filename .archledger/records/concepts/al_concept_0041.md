---
schema_version: 2
id: al_concept_0041
type: concept
title: "JSON output envelope contract"
status: proposed
section: cross_cutting_concepts
order: 20
date: "2026-05-23"
applies_to: []
body_format: markdown
created_at: "2026-05-23T12:31:00Z"
updated_at: "2026-05-23T12:31:00Z"
---

When `--json` is passed, every CLI command emits a JSON envelope: `{"ok": bool, "command": str, "result_type": str, "result": ..., "events": [...], "warnings": [...]}`. On error, the envelope includes `error` with `code`, `message`, `details`, and `remediation`. This shape is a public API contract tested by `test_json_contracts.py`. Exit codes map deterministically to error categories.
