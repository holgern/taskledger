# Taskledger CLI Command Contract

Taskledger uses a task-first command grammar:

```text
taskledger [--root PATH] [--json] <area> <verb> [RESOURCE_REF] [--task TASK_REF] [options]
```

## Global Options

- `--root PATH` selects the workspace root.
- `--json` is root-level only and must appear before the command group.
- Command-local `--json` options are not part of the public contract.

`--cwd` remains accepted as a compatibility root alias, but docs and examples should
prefer `--root`.

## Task Scoping

Task-scoped commands default to the active task. Use `--task TASK_REF` only when
explicitly targeting another task.

Examples:

```bash
taskledger plan start
taskledger plan start --task task-0001
taskledger implement finish --task task-0001 --summary "Implemented."
taskledger validate status --task task-0001
```

Optional positional task refs are not supported.

## Positional Resource Refs

Positional refs are reserved for the direct resource being changed or shown:

```bash
taskledger task activate TASK_REF
taskledger todo done TODO_ID --task TASK_REF --evidence "pytest -q"
taskledger question answer QUESTION_ID --task TASK_REF --text "Yes."
taskledger handoff show HANDOFF_ID --task TASK_REF
taskledger require add REQUIRED_TASK_REF --task TASK_REF
```

## Removed Pre-Release Aliases

These aliases are intentionally not registered:

- `task new`
- `task clear-active`
- `implement add-change`
- `validate add-check`
- `file link`
- `file unlink`
- `link link`
- `link unlink`

Use `task create`, `task deactivate`, `implement change`, `validate check`,
`file add`, `file remove`, `link add`, and `link remove` instead.

## Approval Escape Hatches

Plan approval escape hatches require `--reason` to prevent silent bypass:

| Flag                     | Effect                                           | Requires `--reason`   |
| ------------------------ | ------------------------------------------------ | --------------------- |
| `--allow-empty-criteria` | Skip the acceptance criteria requirement         | Yes                   |
| `--allow-open-questions` | Approve despite open planning questions          | Yes                   |
| `--allow-empty-todos`    | Approve despite no todos in the plan             | Yes                   |
| `--no-materialize-todos` | Skip materializing plan todos into the checklist | Yes                   |
| `--allow-agent-approval` | Allow agent (non-user) approval                  | Yes (plus `--reason`) |

Approval also requires `--note` for user approval. Agent approval additionally
requires `--allow-agent-approval --reason "..."`.

## Todo Source Inference

When `todo add` is called without an explicit `--source`, the source is
inferred from the active lock:

| Active lock stage | Inferred source |
| ----------------- | --------------- |
| `implementing`    | `implementer`   |
| `planning`        | `planner`       |
| No active lock    | `user`          |

Plan-materialized todos always use `source=plan`.
