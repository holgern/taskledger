---
schema_version: 2
id: al_content_0003
type: section
section: context_and_scope
title: Context and Scope
order: 30
status: accepted
date: "2026-05-23"
body_format: markdown
created_at: "2026-05-23T12:24:46Z"
updated_at: "2026-05-23T12:24:46Z"
---

taskledger operates as a self-contained tool within a software development project. It interacts with four categories of external actors:

1. **Agent harnesses** (opencode, codex, chatgpt, etc.) invoke taskledger CLI commands to create tasks, propose plans, log implementation changes, run validation checks, and manage handoffs. They consume `--json` output.
2. **Human developers** use the CLI directly in terminals for task creation, plan review, approval, lock management, and inspection (`status`, `context`, `next-action`, `doctor`).
3. **CI systems** may invoke taskledger for status checks, validation, or snapshot/export operations.
4. **Python library consumers** import from `taskledger.api.*` to programmatically manage tasks without the CLI subprocess.

The system boundary is the `.taskledger/` directory and the `taskledger.toml` config file at the project root. Everything inside `.taskledger/` is taskledger-owned state. Everything outside is the host project's source code.

taskledger does not depend on any external services, databases, or network endpoints. It reads the host project's file system for search/symbol operations but does not modify files outside `.taskledger/`.
