---
schema_version: 2
id: al_content_0011
type: section
section: risks_and_technical_debt
title: Risks and Technical Debt
order: 110
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

Known risks and areas of technical debt:

- **Storage scaling with many tasks**: Each task is a directory with multiple sidecar files. Very large projects (hundreds of tasks) may see slowdowns in list/query operations since indexes are rebuilt from file scans.
- **Migration surface between storage versions**: The storage layout has evolved (currently v3). Migration code in `taskledger/storage/migrations.py` adds complexity. Future format changes must maintain backward compatibility.
- **Service boundary erosion**: Some service modules (notably `tasks.py`) have grown large. The service layer has no formal interface contracts — boundaries are enforced by convention and tests (`test_service_boundaries.py`).
- **Growing dependency count**: Jinja2 is used only for HTML report templates. The dependency is justified by the `serve` and `task report` features but adds weight for users who only need the CLI.
