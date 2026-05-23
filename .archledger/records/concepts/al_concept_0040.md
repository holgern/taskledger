---
schema_version: 2
id: al_concept_0040
type: concept
title: "Actor metadata and role semantics"
status: proposed
section: cross_cutting_concepts
order: 10
date: "2026-05-23"
applies_to: []
body_format: markdown
created_at: "2026-05-23T12:30:59Z"
updated_at: "2026-05-23T12:30:59Z"
---

Every mutation carries an `ActorRef` (type: agent/user/system, name, role, session ID, harness ID) and optionally a `HarnessRef` (harness identity, kind, capabilities). The system distinguishes user-only actions (plan approval, criterion waivers) from agent actions. Actor metadata is persisted in locks, runs, events, and handoff records for audit trails.

Source: `taskledger/domain/actor.py` (`ActorRef`, `HarnessRef`), `taskledger/domain/states.py` (`ActorType`, `ActorRole`, `HarnessKind`).
