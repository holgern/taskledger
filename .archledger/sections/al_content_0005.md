---
schema_version: 2
id: al_content_0005
type: section
section: building_block_view
title: Building Block View
order: 50
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

The top-level building block is the **taskledger system**, decomposed into five black-box components:

1. **CLI Layer** — Handles command parsing, task reference resolution, and output rendering.
2. **API Layer** — Provides stable Python function wrappers around service operations.
3. **Services Layer** — Orchestrates lifecycle flows, handoffs, and inspection.
4. **Domain Layer** — Defines models, state machines, and policy decisions.
5. **Storage Layer** — Manages file system persistence and layout.

Data flows strictly downward: CLI → Services → Domain + Storage. The API layer calls Services directly. The Domain layer has no dependencies on Storage or Services.

Each task is stored as a **task bundle directory** under `.taskledger/` containing the task record (Markdown) and sidecar collections for plans, runs, locks, todos, questions, events, changes, checks, handoffs, and links.
