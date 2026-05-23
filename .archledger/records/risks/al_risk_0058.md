---
schema_version: 2
id: al_risk_0058
type: risk
title: "Migration surface between storage versions"
status: proposed
section: risks_and_technical_debt
order: 20
date: "2026-05-23"
severity: medium
probability: medium
mitigation: "Doctor checks detect version mismatches; migration checks flag incompatible records."
body_format: markdown
created_at: "2026-05-23T12:31:19Z"
updated_at: "2026-05-23T12:31:19Z"
---

The storage layout has evolved through multiple versions (currently v3). Migration code in `taskledger/storage/migrations.py` adds complexity. Future format changes must maintain backward compatibility or provide migration paths. Mitigation: `doctor` checks detect version mismatches; migration checks in `doctor_checks/migration_checks.py`.
