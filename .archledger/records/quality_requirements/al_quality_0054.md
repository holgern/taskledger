---
schema_version: 2
id: al_quality_0054
type: quality_requirement
title: "JSON envelope output stability"
status: proposed
section: quality_requirements
order: 30
date: "2026-05-23"
category: reliability
source: ""
measure: ""
scenarios: []
body_format: markdown
created_at: "2026-05-23T12:31:18Z"
updated_at: "2026-05-23T12:31:18Z"
---

## Requirement

The JSON output shape (`ok`, `command`, `result_type`, `result`, `events`, `warnings`) must remain stable. Breaking changes to field names, shapes, or semantics require explicit version bumps.

## Measurement

- `test_json_contracts.py` validates envelope shape and field presence for all commands.
- Error envelopes include `code`, `message`, `details`, and `remediation` fields.
