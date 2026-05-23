---
schema_version: 2
id: al_deploy_0039
type: infrastructure
title: "Local development deployment"
status: proposed
section: deployment_view
level: 1
parent: null
order: 10
date: "2026-05-23"
environment: "development"
maps_building_blocks: []
body_format: markdown
created_at: "2026-05-23T12:30:52Z"
updated_at: "2026-05-23T12:30:52Z"
---
**Node**: Developer workstation or CI runner

**Software**:
- Python 3.10+
- taskledger (pip installed)
- Host project with `taskledger.toml` config

**Storage**:
- `.taskledger/` directory in project root (Markdown/YAML front matter files)
- JSON index caches under `.taskledger/indexes/`
- Project config at `taskledger.toml`

**Network**: None required. Optional: `taskledger serve` starts a local HTTP dashboard.

**Installation**: `pip install taskledger` or `pip install -e .` from source. Single entry point: `taskledger` CLI.
