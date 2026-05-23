---
schema_version: 2
id: al_adr_0051
type: adr
title: "External skill packaging"
status: proposed
section: architecture_decisions
order: 60
date: "2026-05-23"
deciders: []
supersedes: []
related: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:31:04Z"
updated_at: "2026-05-23T12:31:04Z"
---

## Context

Agent skill files (SKILL.md) provide integration instructions for coding agents. Need to decide where they live relative to the Python package.

## Decision

Skills live under `skills/taskledger/` in the repository, outside the `taskledger` Python package. They are not packaged as Python package data, not loaded via `importlib.resources`, and not distributed via PyPI as part of the package.

## Consequences

- Positive: Clean separation between tool functionality and agent integration instructions.
- Positive: Skills can be versioned independently and distributed through different channels.
- Negative: Skill installation is a separate step from package installation.

## Alternatives considered

- Package skills as package data: Coupling skill version to package version, harder to update independently.
- Load skills via importlib.resources: Adds packaging complexity and coupling.
