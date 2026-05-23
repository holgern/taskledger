---
schema_version: 2
id: al_glossary_0073
type: glossary_term
title: "Worker Pipeline"
status: proposed
section: glossary
order: 130
date: "2026-05-23"
term: "Worker Pipeline"
definition: "An optional advisory overlay that guides fresh-context handoffs through sequential worker steps."
body_format: markdown
created_at: "2026-05-23T12:31:26Z"
updated_at: "2026-05-23T12:31:26Z"
---

An optional advisory overlay configured in `taskledger.toml` that guides fresh-context handoffs through a sequence of worker steps (e.g., planner → tester → implementer → reviewer). Worker pipelines do not override lifecycle gates — they are advisory workflow guidance. Configured via `taskledger/storage/worker_pipeline_config.py`.
