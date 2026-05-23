---
schema_version: 2
id: al_block_0032
type: black_box
title: "Services Layer"
status: proposed
section: building_block_view
level: 1
parent: al_block_0029
order: 30
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

Orchestrates lifecycle flows by coordinating between Domain (policies, models) and Storage (persistence). Key modules: `tasks.py` (core lifecycle operations), `planning_flow.py`, `implementation_flow.py`, `validation_flow.py`, `handoff.py` + `handoff_lifecycle.py`, `doctor.py`, `navigation.py`, `worker_pipeline.py`, `dashboard.py`. Services gather context from storage, call domain policies, and persist results.
