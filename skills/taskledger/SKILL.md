---
name: taskledger
description: Manage staged coding tasks with plan approval, implementation logging, validation, locks, and fresh-context handoffs
license: Apache-2.0
compatibility: opencode
metadata:
  audience: coding-agents
  workflow: task-management
---

## When to use this skill

Use taskledger for staged coding work that needs a durable task record, reviewable plan, explicit user approval, implementation log, validation evidence, and fresh-context continuation.

## Never do these things

- Do not implement before `taskledger plan approve` has recorded user approval.
- Do not validate before implementation has been finished.
- Do not manually edit ledger files except through documented repair.
- Do not break locks without a reason.
- Do not mark validation passed without checking every mandatory acceptance criterion.
- Do not inline large source files into taskledger records by default; use `@path` references.

## Fresh context entry protocol

1. Run `taskledger next-action <task>`.
2. Run `taskledger context <task> --for planning|implementation|validation --format markdown`.
3. Inspect `taskledger lock show <task>` before active work.
4. Use `taskledger can <task> implement` or `taskledger can <task> validate` before those stages.

## Planning protocol

1. `taskledger task create <slug> --description "..."`
2. `taskledger plan start <task>`
3. Add questions with `taskledger question add <task> --text "..."` when decisions are missing.
4. Propose a plan with acceptance criteria: `taskledger plan propose <task> --criterion "..." --file ./plan.md`.
5. Wait for user review.
6. Record approval only with user intent: `taskledger plan approve <task> --version N --actor user --note "..."`.

## Implementation protocol

1. `taskledger context <task> --for implementation --format markdown`
2. `taskledger implement start <task>`
3. Make the code changes.
4. Log work with `taskledger implement log <task> --message "..."`.
5. Log file changes with `taskledger implement change <task> --path ... --kind edit --summary "..."`.
6. Optionally capture Git evidence with `taskledger implement scan-changes <task> --from-git --summary "..."`.
7. `taskledger implement finish <task> --summary "..."`

## Validation protocol

1. `taskledger context <task> --for validation --format markdown`
2. `taskledger validate start <task>`
3. Run checks outside taskledger.
4. Record each criterion result: `taskledger validate check <task> --criterion ac-0001 --status pass|fail|warn|not_run --evidence "..."`
5. Finish with `taskledger validate finish <task> --result passed|failed|blocked --summary "..."`

## Required logging

- Log every meaningful implementation change.
- Record deviations from the approved plan.
- Store failed validation; do not hide it.
- Use `taskledger link add <task> --path ... --kind code|test|doc|config|dir|other` for files that matter to the task.
- Use `taskledger todo done <task> <todo-id>` when mandatory todos are completed.

## Failure handling

- If a lock is stale, inspect it first, then run `taskledger lock break <task> --reason "..."`.
- If validation fails, record the failure and return to implementation or replanning.
- If indexes are stale, run `taskledger repair index`; `taskledger reindex` is a compatibility alias.
- If dependencies must be bypassed, only a user waiver may unblock implementation.

## Command examples

```bash
taskledger context task-0001 --for implementation --format markdown
taskledger implement change task-0001 --path taskledger/services/tasks.py --kind edit --summary "Hardened validation gates."
taskledger validate check task-0001 --criterion ac-0001 --status pass --evidence "uv run pytest -q"
taskledger task dossier task-0001 --format markdown
```
