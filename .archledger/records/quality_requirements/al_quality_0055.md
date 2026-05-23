---
schema_version: 2
id: al_quality_0055
type: quality_requirement
title: "Lifecycle gate correctness"
status: proposed
section: quality_requirements
order: 40
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

Every stage transition must pass through policy gates. Invalid transitions must fail with specific error codes and messages. User-only actions (approval, waivers) must be enforced.

## Measurement

- `test_domain_policies.py` covers all policy decision functions.
- `test_lifecycle_policies.py` covers stage transition rules.
- `test_plan_approval_contract.py` covers user-only approval semantics.
