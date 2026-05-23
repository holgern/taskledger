---
schema_version: 2
id: al_quality_0056
type: quality_requirement
title: "Export/import round-trip fidelity"
status: proposed
section: quality_requirements
order: 50
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

Export/import must preserve all taskledger state exactly. Importing an archive into a fresh workspace must reproduce the original state including tasks, plans, runs, locks, events, handoffs, and active task selection.

## Measurement

- Export/import tests verify round-trip fidelity.
- Active task state must survive export/import.
