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
- Do not break locks for normal actor or harness transfer; use durable handoffs.
- Do not mark validation passed without checking every mandatory acceptance criterion.
- Do not inline large source files into taskledger records by default; use `@path` references.
- Do not import or call `taskledger.storage.*`, `taskledger.services.*`, or `taskledger.domain.*` from ad-hoc Python during normal task work. Use CLI commands or public `taskledger.api.*` only.
- Do not use repair commands (`lock break`, `repair lock`, `repair task`, `repair index`) in the normal lifecycle. Use them only after `doctor`/`lock show` proves there is stale or corrupted state.
- Do not pass approval escape hatches such as `--allow-empty-criteria`, `--allow-open-questions`, or `--allow-agent-approval` unless the user explicitly requested that bypass and gave a reason.

## Fresh context entry protocol

1. Run `taskledger actor whoami`.
2. Run `taskledger task active`.
3. Run `taskledger next-action`.
4. Run `taskledger context --for planning|implementation|validation --format markdown`.
5. Inspect `taskledger lock show` before active work.
6. Use `taskledger can implement` or `taskledger can validate` before those stages.
7. If a durable handoff exists, claim it with `taskledger handoff claim handoff-0001` before continuing and close it after the intended next action starts.

## Actor and harness protocol

1. Before mutating taskledger state, verify identity with `taskledger actor whoami`.
2. If identity is wrong, set `TASKLEDGER_ACTOR_TYPE`, `TASKLEDGER_ACTOR_NAME`, `TASKLEDGER_ACTOR_ROLE`, `TASKLEDGER_HARNESS`, and `TASKLEDGER_SESSION_ID`.
3. Never claim to be a user unless the user explicitly instructed it.
4. User-only actions remain user-only: plan approval, acceptance criterion waivers, and dependency waivers.
5. For handoffs, use `--intended-actor` and `--intended-harness` to document the target actor and harness.

## Planning protocol

1. `taskledger task new "Short task request"` when creating a fresh task.
2. For existing tasks, `taskledger task activate <slug>`.
3. `taskledger plan start`
4. Add questions with `taskledger question add --text "..." --required-for-plan` when decisions are missing.
5. Stop after asking required questions; do not invent answers.
6. After the user answers, run `taskledger question status`.
7. Review all answered questions with `taskledger question answers` before regenerating the plan.
8. Regenerate from answers with `taskledger plan regenerate --from-answers --file ./plan.md`.
9. Ensure the plan front matter includes `acceptance_criteria` and `todos`; approved plan todos materialize into the implementation checklist.
10. For diagnostic commands needed to build the plan, preserve their output in a linked artifact or use `taskledger plan command -- ...`.
11. A proposed plan must include concrete `acceptance_criteria` and `todos` in front matter unless the user explicitly says the task is trivial.
12. After `taskledger plan propose`, do not run `taskledger lock break`; planning locks are released by proposal. Run `taskledger next-action`.
13. Record approval only with user intent: `taskledger plan approve --version N --actor user --note "..."`.

The plan file should use version ids like `plan-v1`, `plan-v2` in references. Do not use zero-padded forms.

## Implementation protocol

1. `taskledger context --for implementation --format markdown`
2. `taskledger implement start`
3. `taskledger implement checklist` - review the mandatory and optional todo checklist before starting.
4. If no todos exist, create a concrete checklist: `taskledger todo add --text "..."`
5. Work one todo at a time:
   - Make the code changes
   - `taskledger implement change --path ... --kind edit --summary "..."`
   - Run verification through `taskledger implement command -- ...` so exit code and output are recorded.
   - Mark each todo done only after the relevant command or inspection evidence exists: `taskledger todo done <todo-id> --evidence "implement command change-NNNN exited 0"`
6. `taskledger implement checklist` after each meaningful change to track progress.
7. Do not run `implement finish` until `todo status` says all todos are complete.
8. `taskledger implement finish --summary "Completed all implementation todos..."`

**Critical**: `implement finish` will block until all non-skipped todos are done. Use `todo status` to verify readiness.

## Validation protocol

1. `taskledger context --for validation --format markdown`
2. `taskledger validate start`
3. Check `taskledger validate status` to see current validation state and blockers.
4. Run verification checks outside taskledger.
5. Record criterion results: `taskledger validate check --criterion ac-0001 --status pass|fail|warn|not_run --evidence "..."`
6. Optionally waive criteria with user authority: `taskledger validate waive --criterion ac-0001 --reason "..."`.
7. Check `taskledger validate status` again to confirm all mandatory gates pass.
8. Finish with `taskledger validate finish --result passed|failed|blocked --summary "..."`

### Recovery Rules

- If validation fails, record the failure and do not hide it.
- Run `taskledger validate status` to inspect all blocking issues before finishing.
- Use `taskledger handoff validation-context` to prepare context for agent continuation after validation failure.

### Waiver Rules

- Only user actors can waive acceptance criteria.
- Each waiver must include a reason and is permanently recorded in the validation history.
- Waived criteria are marked as satisfied for gate checking but remain visible in status reports.

## Required logging

- Every implementation run must have a todo checklist unless the user explicitly says the task is too small.
- Log every meaningful implementation change with `taskledger implement change`.
- Record deviations from the approved plan with `taskledger implement deviation`.
- Mark todos done with evidence: `taskledger todo done <todo-id> --evidence "pytest -q"`.
- Use `taskledger handoff create --mode implementation|validation --intended-actor agent --intended-harness codex` when switching actor or harness.
- Use `taskledger handoff claim handoff-0001` before continuing work from a handoff.
- Use `taskledger link add --path ... --kind code|test|doc|config|dir|other` for files that matter.
- Store failed validation; do not hide it.

## Handoff protocol

Use durable handoffs when switching harnesses or switching between human and agent work.

To hand work to another actor:

1. Run `taskledger handoff create --mode implementation|validation --intended-actor agent|user --intended-harness codex --summary "..."`
2. Do not break a lock for normal transfer.
3. Tell the receiving actor to claim the handoff before continuing.

To receive work:

1. Run `taskledger actor whoami`.
2. Run `taskledger handoff claim handoff-0001`.
3. Run `taskledger next-action`.
4. Run `taskledger context --for implementation|validation --format markdown`.

## Never do these things

- Do not finish implementation while `taskledger todo status` shows open, active, or blocked todos.
- Do not skip mandatory todos unless the user explicitly authorizes the skip with a reason.
- Do not rely on prior chat context when a taskledger handoff exists; claim and read the durable context.

## Failure handling

- If a lock is stale, inspect it first, then run `taskledger lock break --reason "..."`.
- If validation fails, record the failure and return to implementation or replanning.
- If indexes are stale, run `taskledger repair index`; `taskledger reindex` is a compatibility alias.
- If dependencies must be bypassed, only a user waiver may unblock implementation.

## Command examples

```bash
taskledger actor whoami
taskledger task new "Parser fix" --slug parser-fix
taskledger question add --text "Should legacy storage be removed?" --required-for-plan
taskledger question status
taskledger question answers
taskledger question list --status answered
taskledger plan regenerate --from-answers --file ./plan.md
taskledger context --for implementation --format markdown
taskledger implement change --path taskledger/services/tasks.py --kind edit --summary "Hardened validation gates."
taskledger todo done todo-0001 --evidence "uv run pytest -q" --artifact tests/test_parser.py
taskledger validate check --criterion ac-0001 --status pass --evidence "uv run pytest -q"
taskledger handoff create --mode validation --intended-actor agent --intended-harness codex --summary "Ready for validation."
taskledger task dossier --format markdown
```
