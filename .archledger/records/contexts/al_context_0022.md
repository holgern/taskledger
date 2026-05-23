---
schema_version: 2
id: al_context_0022
type: context_interface
title: "CI systems"
status: proposed
section: context_and_scope
order: 30
date: "2026-05-23"
context_kind: "technical"
partner: "CI runner"
inputs: []
outputs: []
channels: []
body_format: markdown
created_at: "2026-05-23T12:29:56Z"
updated_at: "2026-05-23T12:29:56Z"
---

CI runners invoke taskledger commands in automated pipelines. Key interactions: `status --json`, `doctor`, `validate`, `export`, `snapshot`. CI relies on deterministic exit codes to gate pipeline stages.
