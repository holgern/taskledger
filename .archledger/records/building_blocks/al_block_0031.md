---
schema_version: 2
id: al_block_0031
type: black_box
title: "API Layer"
status: proposed
section: building_block_view
level: 1
parent: al_block_0029
order: 20
date: "2026-05-23"
interfaces: []
location: []
fulfilled_requirements: []
risks: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:30:27Z"
updated_at: "2026-05-23T12:30:27Z"
---

Stable Python function wrappers under `taskledger/api/` that mirror the CLI surface for programmatic use. Each module (tasks, plans, handoff, locks, etc.) exposes functions that accept workspace paths and return dictionaries matching the JSON output shape. The API layer calls Services directly.
