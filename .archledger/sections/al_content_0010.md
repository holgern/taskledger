---
schema_version: 2
id: al_content_0010
type: section
section: quality_requirements
title: Quality Requirements
order: 100
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

Quality requirements that gate architectural decisions:

- **Data integrity**: Atomic writes and strict front matter validation prevent corrupt state. Partial writes are impossible due to `os.replace` semantics.
- **CLI exit code contract**: Exit codes are stable and tested. Agents and CI pipelines rely on specific codes for automation.
- **JSON envelope stability**: The JSON output shape (`ok`, `command`, `result_type`, `result`) is a public API contract. Breaking changes require explicit versioning.
- **Lifecycle gate correctness**: Every stage transition is validated by policy functions with full test coverage of error paths.
- **Export/import round-trip**: Archives preserve all state. Import into a fresh workspace reproduces the original taskledger state exactly.
