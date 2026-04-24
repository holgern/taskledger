---
name: taskledger
description: Manage staged coding tasks with plan approval, implementation logging, validation, locks, and fresh-context handoffs
license: Apache-2.0
compatibility: opencode
metadata:
  audience: coding-agents
  workflow: task-management
---

## What I do

- Create durable coding tasks.
- Store reviewable plan versions.
- Enforce stage gates before implementation and validation.
- Use visible task locks during active stages.
- Record implementation logs, code changes, todos, and validation results.
- Produce handoff context for fresh agent sessions.

## Rules

- Do not implement before an accepted plan exists.
- Do not validate before implementation is finished.
- Use `taskledger next-action <task>` before choosing the next operation.
- Use `taskledger can <task> implement` or `taskledger can <task> validate` before active work.
- Start active stages with the matching start command.
- Log code changes with `taskledger implement add-change`.
- Store validation results even when validation fails.
- Break locks only with an explicit reason.

## Planning workflow

1. `taskledger task create ...`
2. `taskledger plan start <task>`
3. `taskledger question add <task> --text "..."`
4. `taskledger plan propose <task> --file ./plan.md`
5. Wait for review.
6. `taskledger plan approve <task> --version N`

## Implementation workflow

1. `taskledger handoff implementation-context <task> --format markdown`
2. `taskledger implement start <task>`
3. Perform code changes.
4. `taskledger implement log <task> --message "..."`
5. `taskledger implement add-change <task> --path ... --kind edit --summary "..."`
6. `taskledger implement finish <task> --summary "..."`

## Validation workflow

1. `taskledger handoff validation-context <task> --format markdown`
2. `taskledger validate start <task>`
3. Run checks.
4. `taskledger validate add-check <task> --name "..." --status pass|fail|warn|not_run`
5. `taskledger validate finish <task> --result passed|failed|blocked --summary "..."`

## Recovery

- `taskledger lock show <task>`
- `taskledger lock break <task> --reason "..."`
- `taskledger doctor`
- `taskledger reindex`
