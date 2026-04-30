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
- Do not use repair commands (`lock break`, `repair lock`, `repair run`, `repair task`, `repair index`) in the normal lifecycle. Use them only after `doctor`/`lock show` proves there is stale or corrupted state.
- Do not pass approval escape hatches such as `--allow-empty-criteria`, `--allow-open-questions`, `--allow-empty-todos`, `--no-materialize-todos`, `--allow-lint-errors`, or `--allow-agent-approval` unless the user explicitly requested that bypass and gave a reason. All escape hatches require `--reason`.

## Fresh context entry protocol

1. Run `taskledger actor whoami`.
2. Run `taskledger task active`.
3. Run `taskledger next-action`.
   - Treat this as the preferred fresh-context entrypoint.
   - Inspect `next_item` before parsing prose.
   - Run `next_command` when it is safe and appropriate.
   - Do not invent question answers, evidence, or approval notes.
4. Run `taskledger context --for planning|implementation|validation --format markdown`.
5. Inspect `taskledger lock show` before active work.
6. Use `taskledger can implement` or `taskledger can validate` before those stages.
   - Use `taskledger can implement-resume` when `next-action` recommends resuming an existing implementation run.
7. If a durable handoff exists, claim it with `taskledger handoff claim handoff-0001` before continuing and close it after the intended next action starts.

Example human output:

```text
todo-work: Implementation is in progress; 1 todos remain.
Next todo: todo-0001 -- Update next-action JSON payload.
Command: taskledger todo show todo-0001
Mark todo done after evidence exists: taskledger todo done todo-0001 --evidence "..."
Progress: 0/1 todos done
```

## Actor and harness protocol

1. Before mutating taskledger state, verify identity with `taskledger actor whoami`.
2. If identity is wrong, use `taskledger actor set --type <type> --name <name> [--role <role>] [--tool <tool>]` and `taskledger harness set --name <name> [--kind <kind>]` to persist the correct identity.
3. Alternatively, set `TASKLEDGER_ACTOR_TYPE`, `TASKLEDGER_ACTOR_NAME`, `TASKLEDGER_ACTOR_ROLE`, `TASKLEDGER_HARNESS`, and `TASKLEDGER_SESSION_ID` environment variables. Env vars take priority over stored values.
4. Use `taskledger actor clear` and `taskledger harness clear` to remove stored identity and revert to env/auto-detection.
5. Never claim to be a user unless the user explicitly instructed it.
6. User-only actions remain user-only: plan approval, acceptance criterion waivers, and dependency waivers.
7. For handoffs, use `--intended-actor` and `--intended-harness` to document the target actor and harness.

## CLI failure protocol

If any `taskledger ...` command fails with a Python traceback before taskledger emits a normal human or JSON error:

1. Stop issuing mutating taskledger commands immediately.
2. Do not retry the same mutation with different text.
3. Run exactly one read-only health probe: `taskledger actor whoami`.
4. If the health probe fails with the same import traceback, report that taskledger CLI startup is broken and no ledger mutation was recorded.
5. If the health probe succeeds, rerun the failed command once, then continue.
6. For repeated setup mutations, prefer batch commands such as `question add-many` when available.

## Planning protocol

1. `taskledger task create "Short task request" --slug <slug>` when creating a fresh task.
2. `taskledger task activate <slug>` to activate the newly created task for planning.
3. For existing tasks, `taskledger task activate <slug>`.
4. `taskledger plan start`
5. Add questions with `taskledger question add --text "..." --required-for-plan` when decisions are missing.
   - Use `taskledger question add-many --required-for-plan --text $'Question 1\nQuestion 2'` when you already know multiple questions.
6. Ask the questions directly in the harness chat. Do not ask the user to run `taskledger question answer`.
7. Stop after asking required questions; do not invent answers.
8. When the user answers in chat, record the answers yourself with `taskledger question answer-many` or `taskledger question answer`.
9. Run `taskledger question status` and review all answered questions with `taskledger question answers` before writing the plan.
10. Before reading source files to discover plan format, run `taskledger plan template --from-answers --file ./plan.md` when answered questions exist, or `taskledger plan template --file ./plan.md` for a fresh plan skeleton.
11. If answered questions exist, write the next plan with `taskledger plan upsert --from-answers --file ./plan.md`.
12. Use `taskledger plan upsert --file ./plan.md` for plans that are not based on newly answered questions.
13. Ensure the plan front matter includes `acceptance_criteria` and `todos`; approved plan todos materialize into the implementation checklist.
14. For diagnostic commands needed to build the plan, preserve their output in a linked artifact or use `taskledger plan command -- ...`.
15. A proposed plan must include concrete `acceptance_criteria` and `todos` in front matter unless the user explicitly says the task is trivial.
16. After writing the plan, do not run `taskledger lock break`; planning locks are released by plan proposal/upsert. Run `taskledger next-action`.
17. After `taskledger plan upsert --from-answers`, run `taskledger question status`. If it still reports `Plan regeneration needed: True`, do not ask for approval. Inspect `taskledger question answers`, `taskledger plan show --version N`, and `taskledger doctor`.
18. Before asking the user to approve, run `taskledger plan lint --version N` and fix lint errors. Do not ask for approval on plans with lint errors.
19. Record approval only with clear user intent such as approve, accept, go ahead, or start implementation: `taskledger plan approve --version N --actor user --note "User approved in harness: ..."` or `taskledger plan accept --version N --note "User approved in harness: ..."`.

The plan file should use version ids like `plan-v1`, `plan-v2` in references. Do not use zero-padded forms.

## Implementation protocol

1. `taskledger context --for implementation --format markdown`
2. `taskledger implement start`
   - If validation already failed and the plan is still correct, prefer `taskledger implement restart --summary "Fix failed validation findings."`
   - If implementation start fails because another run is already running, stop and run `taskledger doctor`, not only `taskledger doctor locks`.
   - Do not edit project code until implementation has started or a valid implementation resume command succeeds.
3. `taskledger implement checklist` - review the mandatory and optional todo checklist before starting.
4. If no todos exist, create a concrete checklist: `taskledger todo add --text "..."`. Todo source is inferred automatically from the active lock: `implementer` during implementation, `planner` during planning, `user` otherwise.
5. Work one todo at a time:
   - Make the code changes
   - `taskledger implement change --path ... --kind edit --summary "..."`
   - Run verification through `taskledger implement command -- ...` so exit code and output are recorded.
   - Mark each todo done only after the relevant command or inspection evidence exists: `taskledger todo done <todo-id> --evidence "implement command change-NNNN exited 0"`.
   - Optional: add `--source planner|implementer|user` to override the inferred source, though this is rarely needed.
6. `taskledger implement checklist` after each meaningful change to track progress.
7. Do not run `implement finish` until `todo status` says all todos are complete.
8. `taskledger implement finish --summary "Completed all implementation todos..."`

**Critical**: `implement finish` will block until all non-skipped todos are done. Use `todo status` to verify readiness.

## Post-completion follow-up deltas

When a task is done and the user requests a small later change, do not reopen or mutate the completed task. Create a follow-up task linked to the completed parent:

```bash
taskledger task follow-up PARENT_REF "Short delta title" --description "..." --activate
```

Then run the normal compact lifecycle on the follow-up task. Keep the plan small, but preserve approval, implementation evidence, and validation evidence.

## Compact implementation loop

For routine same-session implementation, prefer the next action and the single
next todo over a broad generated context read:

```bash
taskledger --json next-action
taskledger --json todo next
taskledger todo show todo-0003
# implement only that todo
pytest tests/...
taskledger todo done todo-0003 --evidence "pytest tests/... passed"
taskledger --json next-action
```

Rules for agents:

1. Prefer `next-action` and `todo next` over generated context during normal work.
2. Use `validation_hint` before marking a todo done.
3. Mark a todo done only after evidence exists.
4. Record concise evidence.
5. Do not create handoffs or context bundles unless the user explicitly asked to switch harness or session.

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
- If validation fails because implementation has a bug, finish validation as failed, run `taskledger next-action`, then restart implementation with `taskledger implement restart`. Use implementation context or an implementation handoff for the next actor.

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
- Use `taskledger file add --path ... --kind code|test|doc|config|dir|other` for files that matter.
- Store failed validation; do not hide it.

## Fresh-worker context protocol

Use focused contexts for one-worker tasks:

- Implement one todo:
  `taskledger context --for implementer --todo todo-0003`
- Review spec compliance for an implementation run:
  `taskledger context --for spec-reviewer --run run-0008`
- Review code quality for an implementation run:
  `taskledger context --for code-reviewer --run run-0008`
- Store durable handoff context before switching harness:
  `taskledger handoff create --mode implementation --todo todo-0003`

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
- If breaking an implementation lock leaves a running implementation run behind, use `taskledger implement resume --reason "..."` instead of `implement start`.
- If `task show` reports `status_stage=implementing` but `active_stage` is missing, do not run `task uncancel`; run `taskledger next-action` and resume when it reports `implement-resume`.
- If a cancelled task is restored with `task uncancel`, run `taskledger next-action` before starting work. If the task still has a running implementation run, resume that run instead of starting a new one.
- If `taskledger next-action` recommends a command but `taskledger can <action>` rejects it, treat this as a lifecycle inconsistency. Run `taskledger doctor` and follow the repair guidance.
- Use `taskledger repair run --task TASK --run RUN --reason "..."` only when diagnostics identify an orphaned running planning run with no matching active lock.
- Never use repair to bypass approval, validation, or active implementation locks.
- If validation fails, record the failure and return to implementation or replanning.
- If indexes are stale, run `taskledger repair index`; `taskledger reindex` is a compatibility alias.
- If a task is truly cancelled and the user wants to continue, use `taskledger task uncancel --reason "..." [--to STAGE]` to restore a safe durable stage before re-entering an active stage.
- If dependencies must be bypassed, only a user waiver may unblock implementation.

## Command examples

```bash
taskledger actor whoami
taskledger actor set --type agent --name my-agent --role implementer
taskledger actor clear
taskledger harness set --name pi --kind agent_harness
taskledger harness clear
taskledger task create "Parser fix" --slug parser-fix
taskledger task follow-up parser-fix "Rename parser copy" --description "Small post-completion delta." --activate
taskledger question add --text "Should legacy storage be removed?" --required-for-plan
taskledger question add-many --required-for-plan --text $'What release boundary should be used?\nShould the changelog include validation evidence?'
taskledger question answer-many --text "q-0001: No."
taskledger question status
taskledger question answers
taskledger question list --status answered
taskledger next-action
taskledger plan template --from-answers --file ./plan.md
taskledger plan upsert --from-answers --file ./plan.md
taskledger plan lint --version 1
taskledger plan accept --version 1 --note "User approved in harness."
taskledger context --for implementation --format markdown
taskledger context --for implementer --todo todo-0003
taskledger context --for spec-reviewer --run run-0008
taskledger context --for code-reviewer --run run-0008
taskledger release tag 0.4.1 --at-task task-0030 --note "0.4.1 released"
taskledger release changelog 0.4.2 --since 0.4.1 --until-task task-0035 --output /tmp/taskledger-0.4.2-changelog-source.md
taskledger implement resume --reason "Reacquire implementation lock for existing running run."
taskledger implement restart --summary "Fix failed validation findings."
taskledger implement change --path taskledger/services/tasks.py --kind edit --summary "Hardened validation gates."
taskledger task uncancel --actor agent --allow-agent-uncancel --reason "User explicitly requested continuation in harness."
taskledger todo done todo-0001 --evidence "uv run pytest -q" --artifact tests/test_parser.py
taskledger validate check --criterion ac-0001 --status pass --evidence "uv run pytest -q"
taskledger handoff create --mode implementation --todo todo-0003 --intended-actor agent --intended-harness codex --summary "Ready for focused implementation."
taskledger handoff create --mode validation --intended-actor agent --intended-harness codex --summary "Ready for validation."
taskledger task dossier --format markdown
```
