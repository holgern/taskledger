---
schema_version: 2
id: al_risk_0057
type: risk
title: "Storage scaling with many tasks"
status: proposed
section: risks_and_technical_debt
order: 10
date: "2026-05-23"
severity: medium
probability: medium
mitigation: "Run reindex after bulk changes; consider task archival for completed work."
body_format: markdown
created_at: "2026-05-23T12:31:19Z"
updated_at: "2026-05-23T12:31:19Z"
---

Each task is a directory with multiple sidecar files. Projects with hundreds of tasks may see slowdowns in list/query operations due to file system scanning. Indexes help but are not always up to date. Mitigation: `reindex` after bulk changes; consider batching for very large projects.
