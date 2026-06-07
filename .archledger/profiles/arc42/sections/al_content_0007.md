---
schema_version: 2
id: al_content_0007
type: section
section: deployment_view
title: Deployment View
order: 70
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

taskledger is a single-node, file-system-based tool. Deployment consists of:

- **Installation**: `pip install taskledger` (PyPI) or local `pip install -e .`
- **Project initialization**: `taskledger init` creates `taskledger.toml` and `.taskledger/` in the project root
- **Runtime**: The CLI runs as a Python process, reading and writing the project's `.taskledger/` directory. No daemon, no server (except optional `taskledger serve` for a local web dashboard).
- **CI integration**: taskledger commands can be run in CI pipelines for status checks and validation
- **Agent integration**: Agent harnesses invoke taskledger CLI commands as subprocess calls
