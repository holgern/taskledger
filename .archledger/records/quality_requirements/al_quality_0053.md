---
schema_version: 2
id: al_quality_0053
type: quality_requirement
title: "CLI exit code contract stability"
status: proposed
section: quality_requirements
order: 20
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

Exit codes must remain stable across versions. Agents and CI pipelines depend on specific codes (0, 2, 3, 4, 5, 6, 7) for automation.

## Measurement

- `test_cli_command_contract.py` verifies exit codes for all command paths.
- `test_json_contracts.py` verifies exit codes alongside JSON output shapes.
