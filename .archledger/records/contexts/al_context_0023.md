---
schema_version: 2
id: al_context_0023
type: context_interface
title: "Python library consumers"
status: proposed
section: context_and_scope
order: 40
date: "2026-05-23"
context_kind: "technical"
partner: "Python import"
inputs: []
outputs: []
channels: []
body_format: markdown
created_at: "2026-05-23T12:29:56Z"
updated_at: "2026-05-23T12:29:56Z"
---

Python code imports from `taskledger.api.*` modules to manage tasks programmatically. The API layer (`taskledger/api/tasks.py`, `taskledger/api/plans.py`, etc.) provides function wrappers that mirror CLI operations without subprocess overhead. Returns dictionaries with the same shapes as JSON output.
