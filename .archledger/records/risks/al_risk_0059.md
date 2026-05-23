---
schema_version: 2
id: al_risk_0059
type: risk
title: "Service boundary erosion"
status: proposed
section: risks_and_technical_debt
order: 30
date: "2026-05-23"
severity: medium
probability: medium
mitigation: "test_service_boundaries.py whitelist tracks allowed cross-module imports and fails on violations."
body_format: markdown
created_at: "2026-05-23T12:31:19Z"
updated_at: "2026-05-23T12:31:19Z"
---

Some service modules (notably `tasks.py` at 1000+ lines) have grown large. The service layer has no formal interface contracts — boundaries are enforced by convention and the `test_service_boundaries.py` whitelist. Mitigation: The whitelist in `docs/service_boundary_whitelist.rst` tracks allowed cross-module imports; the test fails on violations.
