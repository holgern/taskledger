---
schema_version: 2
id: al_constraint_0018
type: constraint
title: "CLI-first with machine-readable JSON output"
status: proposed
section: architecture_constraints
order: 30
date: "2026-05-23"
category: technical
impact: "JSON envelope shape and exit codes are public API contracts; breaking changes require version bumps."
body_format: markdown
created_at: "2026-05-23T12:29:54Z"
updated_at: "2026-05-23T12:29:54Z"
---

The CLI is the primary interface. Every command supports `--json` for machine-readable output with a stable envelope shape (`ok`, `command`, `result_type`, `result`, `events`, `warnings`) and deterministic exit codes. This enables agent harnesses and CI pipelines to consume output programmatically without parsing human text.
