---
schema_version: 2
id: al_risk_0060
type: risk
title: "Growing dependency count"
status: proposed
section: risks_and_technical_debt
order: 40
date: "2026-05-23"
severity: medium
probability: medium
mitigation: "Small dependency set (typer, PyYAML, tomli); each justified by a core feature."
body_format: markdown
created_at: "2026-05-23T12:31:20Z"
updated_at: "2026-06-11T21:00:00Z"
---

The dependency set is small (typer, PyYAML, tomli) and each is justified by a core feature. Risk is low as long as new dependencies are not introduced without explicit justification.
