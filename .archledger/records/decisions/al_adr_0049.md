---
schema_version: 2
id: al_adr_0049
type: adr
title: Typer CLI framework
status: accepted
section: architecture_decisions
order: 40
date: "2026-05-23"
deciders:
  - taskledger maintainers
supersedes: []
related: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:31:03Z"
updated_at: "2026-06-07T11:50:17Z"
source_refs:
  - path: taskledger/cli.py
    role: implements
    reason: Root Typer application and command registration
test_refs:
  - tests/test_help_subprocess.py
---

## Context

Need a CLI framework that supports subcommand groups, type-annotated parameters, and integrates with Click's ecosystem.

## Decision

Use Typer (built on Click) for the CLI. Typer provides type-annotated parameters, subcommand groups, and automatic help generation. The root app in `cli.py` registers nested Typer apps for each command family.

## Consequences

- Positive: Clean type-annotated parameter definitions with `Annotated` types.
- Positive: Click ecosystem compatibility (middleware, testing).
- Negative: Typer adds `click` as a transitive dependency.

## Alternatives considered

- Pure Click: More verbose parameter definitions, no type annotation inference.
- Argparse: Standard library but lacks subcommand ergonomics and type inference.
- Docopt: Declarative but harder to compose nested subcommands.
