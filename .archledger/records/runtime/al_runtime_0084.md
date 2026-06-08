---
schema_version: 2
id: al_runtime_0084
type: runtime_scenario
title: "BDD example to validation evidence"
status: proposed
section: runtime_view
order: 100
date: "2026-06-07"
participants:
  - coding agent
  - taskledger CLI
  - BDD services
  - task storage
trigger: "An actor wants executable examples linked to task acceptance criteria."
result: "External automation results are persisted as traceable validation evidence."
body_format: markdown
created_at: "2026-06-07T11:50:18Z"
updated_at: "2026-06-07T11:50:18Z"
source_refs:
  - path: taskledger/cli_bdd.py
    role: implements
  - path: taskledger/services/bdd_gherkin.py
    role: implements
  - path: taskledger/services/bdd_reports.py
    role: implements
test_refs:
  - tests/test_bdd_cli.py
  - tests/test_bdd_validation_integration.py
---

1. An actor initializes a BDD feature for a managed task and adds rules and Given/When/Then examples.
2. Each example links to acceptance-criterion IDs and may link to Archledger records.
3. `bdd gherkin-export` emits a `.feature` artifact with stable traceability tags.
4. An external BDD runner executes the artifact; taskledger does not run that tool.
5. `validate import-bdd-report` reads Cucumber JSON or JUnit XML, matches scenarios by stable tags, and stores a durable report.
6. Matched results become validation evidence; normal latest-check-wins and mandatory-criterion gates still decide completion.
