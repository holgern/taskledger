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

1. Run `taskledger task active`.
2. Run `taskledger next-action`.
3. Run `taskledger context --for planning|implementation|validation --format markdown`.
4. Inspect `taskledger lock show` before active work.
5. Use `taskledger can implement` or `taskledger can validate` before those stages.

## Planning protocol

1. `taskledger task create <slug> --description "..."`
2. `taskledger task activate <slug>`
3. `taskledger plan start`
4. Add questions with `taskledger question add --text "..."` when decisions are missing.
5. Propose a plan with acceptance criteria: `taskledger plan propose --criterion "..." --file ./plan.md`.
6. Wait for user review.
7. Record approval only with user intent: `taskledger plan approve --version N --actor user --note "..."`.

## Implementation protocol

1. `taskledger context --for implementation --format markdown`
2. `taskledger implement start`
3. Make the code changes.
4. Log work with `taskledger implement log --message "..."`.
5. Log file changes with `taskledger implement change --path ... --kind edit --summary "..."`.
6. Optionally capture Git evidence with `taskledger implement scan-changes --from-git --summary "..."`.
7. `taskledger implement finish --summary "..."`

## Validation protocol

1. `taskledger context --for validation --format markdown`
2. `taskledger validate start`
3. Run checks outside taskledger.
4. Record each criterion result: `taskledger validate check --criterion ac-0001 --status pass|fail|warn|not_run --evidence "..."`
5. Finish with `taskledger validate finish --result passed|failed|blocked --summary "..."`

## Required logging

- Log every meaningful implementation change.
- Record deviations from the approved plan.
- Store failed validation; do not hide it.
- Use `taskledger link add --path ... --kind code|test|doc|config|dir|other` for files that matter to the active task.
- Use `taskledger todo done <todo-id>` when mandatory todos are completed.

## Failure handling

- If a lock is stale, inspect it first, then run `taskledger lock break --reason "..."`.
- If validation fails, record the failure and return to implementation or replanning.
- If indexes are stale, run `taskledger repair index`; `taskledger reindex` is a compatibility alias.
- If dependencies must be bypassed, only a user waiver may unblock implementation.

## Command examples

```bash
taskledger context --for implementation --format markdown
taskledger implement change --path taskledger/services/tasks.py --kind edit --summary "Hardened validation gates."
taskledger validate check --criterion ac-0001 --status pass --evidence "uv run pytest -q"
taskledger task dossier --format markdown
```
