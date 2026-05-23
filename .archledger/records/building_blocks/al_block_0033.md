---
schema_version: 2
id: al_block_0033
type: black_box
title: "Domain Layer"
status: proposed
section: building_block_view
level: 1
parent: al_block_0029
order: 40
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

Pure data models, state enums, normalization, and policy decisions with zero I/O dependencies. Defines `TaskRecord`, `PlanRecord`, `TaskRunRecord`, `TaskLock`, `TaskHandoffRecord`, `TaskEvent`, `ActorRef`, `HarnessRef`, and sidecar types (`TaskTodo`, `FileLink`, `AcceptanceCriterion`, `ValidationCheck`). State machine transitions in `states.py`. Policy decisions in `policies.py` return `Decision` objects. All models have `to_dict()` / `from_dict()` for serialization.
