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
updated_at: "2026-05-23T12:30:29Z"
---

File system persistence for all canonical records. Implements the v2 task bundle layout where each task is a directory with sidecar collections for plans, runs, locks, todos, questions, events, changes, checks, handoffs, and links. Key modules: `task_store.py` (CRUD, layout resolution), `frontmatter.py` (YAML/Markdown serialization), `atomic.py` (atomic writes), `locks.py` (lock file operations), `indexes.py` (index rebuilds), `events.py` (append-only event log), `paths.py` (project discovery), `project_config.py` (taskledger.toml parsing), `migrations.py` (storage version upgrades).
