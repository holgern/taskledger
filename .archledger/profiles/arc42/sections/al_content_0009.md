---
schema_version: 2
id: al_content_0009
type: section
section: architecture_decisions
title: Architecture Decisions
order: 90
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

Key architecture decisions documented as ADR records:

- **ADR-1**: Markdown/YAML front matter as canonical format (not JSON, not SQLite)
- **ADR-2**: JSON indexes as derived rebuildable caches (not authoritative)
- **ADR-3**: Explicit lifecycle gates with policy decisions (not free-form state)
- **ADR-4**: Typer CLI framework (not argparse, not click directly)
- **ADR-5**: Task bundle directory layout (not single-file index)
- **ADR-6**: External skill packaging (skills outside the Python package)
