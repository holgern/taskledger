---
schema_version: 2
id: al_block_0029
type: white_box
title: "taskledger system"
status: proposed
section: building_block_view
level: 1
parent: null
order: 10
date: "2026-05-23"
diagram: null
quality_characteristics: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:30:16Z"
updated_at: "2026-05-23T12:30:16Z"
---

## Motivation

taskledger decomposes into five layers with strict downward dependency flow. This decomposition isolates I/O (storage), business rules (domain), orchestration (services), and presentation (CLI/API).

## Contained building blocks

1. **CLI Layer** (`al_block_0030`) — Typer commands, argument parsing, output rendering
2. **API Layer** (`al_block_0031`) — Stable Python function wrappers
3. **Services Layer** (`al_block_0032`) — Lifecycle orchestration, handoffs, inspection
4. **Domain Layer** (`al_block_0033`) — Models, state machines, policies (no I/O)
5. **Storage Layer** (`al_block_0034`) — File system persistence, atomic writes, layout

## Important interfaces

- CLI → Services: function calls with `workspace_root` + task references
- Services → Domain: policy functions take `PolicyContext`, return `Decision`
- Services → Storage: record CRUD operations via `task_store.py` functions
- API → Services: direct function calls mirroring CLI behavior
