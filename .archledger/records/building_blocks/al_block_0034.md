---
schema_version: 2
id: al_block_0034
type: black_box
title: "Storage Layer"
status: proposed
section: building_block_view
level: 1
parent: al_block_0029
order: 50
date: "2026-05-23"
interfaces: []
location: []
fulfilled_requirements: []
risks: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:30:29Z"
updated_at: "2026-06-11T21:00:00Z"
---

File system persistence for canonical records. Storage layout keeps each task in `.taskledger/ledgers/<ledger_ref>/tasks/<task-id>/`, with independently addressable sidecars including plans, runs, locks, todos, questions, changes, checks, handoffs, links, and code reviews. Ledger-level collections hold events, introductions, releases, and rebuildable indexes. Action/event logging is enabled by default and can be disabled in project config. Project config edits use structured TOML handling rather than ad hoc text replacement.
