---
schema_version: 2
id: al_context_0020
type: context_interface
title: "Agent harnesses"
status: proposed
section: context_and_scope
order: 10
date: "2026-05-23"
context_kind: "technical"
partner: "agent harness (opencode, codex, chatgpt)"
inputs: []
outputs: []
channels: []
body_format: markdown
created_at: "2026-05-23T12:29:55Z"
updated_at: "2026-05-23T12:29:55Z"
---

Agent harnesses invoke taskledger CLI commands as subprocesses. They consume `--json` output and rely on exit codes for automation. Key interactions: `task create`, `plan start`, `plan propose`, `implement start`, `implement log`, `validate start`, `validate check`, `handoff create`, `handoff claim`, `context`. Agents are restricted from user-only actions (plan approval, criterion waivers) by default.
