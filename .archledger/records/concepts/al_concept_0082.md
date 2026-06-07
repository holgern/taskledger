---
schema_version: 2
id: al_concept_0082
type: concept
title: "Durable code-review evidence"
status: proposed
section: cross_cutting_concepts
order: 80
date: "2026-06-07"
applies_to: []
body_format: markdown
created_at: "2026-06-07T11:49:59Z"
updated_at: "2026-06-07T11:49:59Z"
source_refs:
  - path: taskledger/domain/review.py
    role: implements
  - path: taskledger/services/code_review.py
    role: implements
test_refs:
  - tests/test_code_reviews.py
---


Code review is durable evidence attached to a task. A record captures result, summary/body, reviewer and harness, implementation run, worker step, handoff, and optional Git working-tree or commit metadata.

Review records are append-only and may be recorded after a task reaches `done`. They do not create a lifecycle stage, reopen completed work, replace acceptance criteria, or weaken validation completion rules.
