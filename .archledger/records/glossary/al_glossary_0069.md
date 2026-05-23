---
schema_version: 2
id: al_glossary_0069
type: glossary_term
title: "Harness"
status: proposed
section: glossary
order: 90
date: "2026-05-23"
term: "Harness"
definition: "The execution environment running taskledger (agent harness, manual terminal, or CI)."
body_format: markdown
created_at: "2026-05-23T12:31:24Z"
updated_at: "2026-05-23T12:31:24Z"
---

The execution environment running taskledger. Has a kind (agent_harness/manual/ci/unknown), name, session ID, and capabilities. Persisted as `HarnessRef` in `taskledger/domain/actor.py`. Harness metadata is recorded alongside actor metadata in runs and locks.
