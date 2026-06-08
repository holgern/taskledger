---
schema_version: 2
id: al_concept_0081
type: concept
title: "BDD traceability and report evidence"
status: proposed
section: cross_cutting_concepts
order: 70
date: "2026-06-07"
applies_to: []
body_format: markdown
created_at: "2026-06-07T11:49:58Z"
updated_at: "2026-06-07T11:49:58Z"
source_refs:
  - path: taskledger/domain/bdd.py
    role: implements
  - path: taskledger/services/bdd_gherkin.py
    role: implements
  - path: taskledger/services/bdd_reports.py
    role: implements
test_refs:
  - tests/test_bdd_gherkin.py
  - tests/test_bdd_report_import.py
  - tests/test_bdd_validation_integration.py
---

BDD is an optional traceability overlay on a managed task. Features contain rules and Given/When/Then examples. Examples can reference canonical acceptance-criterion IDs and Archledger record IDs.

Gherkin export is an exchange artifact, not canonical state. Stable tags preserve task, example, criterion, and architecture identities. Imported Cucumber JSON or JUnit XML is matched back to examples and persisted as report evidence that can contribute validation checks. Normal lifecycle and validation gates remain authoritative.
