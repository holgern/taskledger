---
schema_version: 2
id: al_glossary_0068
type: glossary_term
title: "Actor"
status: proposed
section: glossary
order: 80
date: "2026-05-23"
term: "Actor"
definition: "The entity performing an action, classified as agent, user, or system."
body_format: markdown
created_at: "2026-05-23T12:31:24Z"
updated_at: "2026-05-23T12:31:24Z"
---

The entity performing an action. Has a type (agent/user/system), name, optional role (planner/implementer/validator/reviewer/operator), session ID, and harness ID. Persisted as `ActorRef` in `taskledger/domain/actor.py`. Actor metadata is recorded in events, locks, runs, and handoffs for audit trails.
