---
schema_version: 2
id: al_content_0004
type: section
section: solution_strategy
title: Solution Strategy
order: 40
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

taskledger uses a layered architecture with clear dependency direction: upper layers depend on lower layers, never the reverse.

1. **CLI Layer** (`taskledger/cli*.py`) — Typer commands that parse arguments, resolve task references, call service functions, and render output (human text or JSON).
2. **API Layer** (`taskledger/api/*.py`) — Stable public wrappers that mirror the CLI surface for programmatic use.
3. **Services Layer** (`taskledger/services/*.py`) — Orchestration logic: lifecycle flows (planning, implementation, validation), handoff rendering, doctor checks, dashboard assembly.
4. **Domain Layer** (`taskledger/domain/*.py`) — Pure data models, state enums, normalization, and policy decisions. No I/O, no file system access.
5. **Storage Layer** (`taskledger/storage/*.py`) — File system operations: front matter read/write, atomic writes, lock files, index rebuilds, migrations.

Key architectural choices:

- **Markdown/YAML front matter as canonical format** — Each record (task, plan, run, lock, handoff, etc.) is stored as a `.md` file with YAML front matter metadata and a Markdown body. This makes state human-readable and Git-friendly.
- **JSON indexes as derived caches** — Index files under `.taskledger/indexes/` are rebuilt from canonical records by `taskledger reindex`. They are never the source of truth.
- **Policy-based gate decisions** — All lifecycle transitions go through functions in `taskledger/domain/policies.py` that return `Decision` objects with `allowed`, `code`, `message`, and `exit_code`. This keeps gate logic testable and separate from I/O.
- **Atomic file writes** — All writes use `atomic_write_text` (write to temp, `os.replace`) to prevent partial writes on crash.
- **Evidence as sidecars** — Code-review records extend traceability without introducing new lifecycle stages or weakening validation gates.

## Maintenance

`ARCHITECTURE.md` in the repository root is generated from archledger source records. Do not edit it directly.

- **Edit**: `.archledger/sections/*.md` for section content, `.archledger/records/**/*.md` for individual records.
- **Regenerate**: Run `archledger build` (or the configured build command) to regenerate `ARCHITECTURE.md`.
- **Verify**: Run `pytest tests/test_docs_and_skill.py tests/test_service_boundaries.py` after changes.
- **Authoritative source**: The archledger records under `.archledger/` are the single source of truth for architecture documentation. `docs/architecture_taskledger_split.rst` is a concise human-maintained summary.
