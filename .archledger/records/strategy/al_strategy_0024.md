---
schema_version: 2
id: al_strategy_0024
type: strategy_item
title: "Layered architecture: CLI \u2192 Services \u2192 Domain \u2192 Storage"
status: accepted
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

The codebase is organized into five layers with target dependency direction: CLI (`taskledger/cli*.py`) → API (`taskledger/api/`) → Services (`taskledger/services/`) → Domain (`taskledger/domain/`) + Storage (`taskledger/storage/`). The Domain layer has no I/O dependencies. Storage owns canonical taskledger persistence and atomic record I/O. Other layers may perform bounded filesystem operations for external inputs/outputs (reports, Git sync, search, CLI file arguments). CLI should prefer API wrappers for public workflows, but current sanctioned exceptions are tracked in `tests/test_service_boundaries.py`.

## Trade-offs

- Clear separation of concerns enables focused testing per layer.
- Service modules can grow large since they orchestrate across domain and storage.
- No formal dependency injection; layer boundaries are enforced by convention and the `test_service_boundaries.py` test.
