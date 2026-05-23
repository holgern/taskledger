---
schema_version: 2
id: al_concept_0045
type: concept
title: "Exit code taxonomy"
status: proposed
section: cross_cutting_concepts
order: 60
date: "2026-05-23"
applies_to: []
body_format: markdown
created_at: "2026-05-23T12:31:01Z"
updated_at: "2026-05-23T12:31:01Z"
---

Stable exit codes for CLI and error classification: 0 (success), 1 (generic failure), 2 (bad input), 3 (workflow rejection — invalid transition, approval required, dependency blocked), 4 (lock conflict — stale lock requires break), 5 (not found / no active task), 6 (storage error / data integrity), 7 (validation failed). Defined in `taskledger/domain/states.py` and `taskledger/errors.py`. Agents and CI pipelines rely on specific codes for automation.
