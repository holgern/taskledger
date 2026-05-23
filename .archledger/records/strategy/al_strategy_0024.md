---
schema_version: 2
id: al_strategy_0024
type: strategy_item
title: "Layered architecture: CLI \u2192 Services \u2192 Domain \u2192 Storage"
status: proposed
section: solution_strategy
order: 10
date: "2026-05-23"
drivers: []
constraints: []
related_adrs: []
body_format: markdown
created_at: "2026-05-23T12:30:14Z"
updated_at: "2026-05-23T12:30:14Z"
---

## Strategy

The codebase is organized into five layers with strict dependency direction: CLI (`taskledger/cli*.py`) → API (`taskledger/api/`) → Services (`taskledger/services/`) → Domain (`taskledger/domain/`) + Storage (`taskledger/storage/`). The Domain layer has no I/O dependencies. Storage is the only layer that touches the file system directly.

## Trade-offs

- Clear separation of concerns enables focused testing per layer.
- Service modules can grow large since they orchestrate across domain and storage.
- No formal dependency injection; layer boundaries are enforced by convention and the `test_service_boundaries.py` test.
