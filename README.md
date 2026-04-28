# taskledger

`taskledger` is a task-first durable state layer for staged coding work. It keeps
project-local configuration in `taskledger.toml` at the workspace root and stores
plans, approval state, implementation logs, validation results, locks, and
fresh-context handoffs under a configurable `taskledger_dir` (default:
`.taskledger/` beside that config file).

## Canonical workflow

```text
task -> plan -> approval -> implement -> validate -> done
```

The supported command surface is organized as:

**Core workflow:**

- `task`, `plan`, `question`, `implement`, `validate`, `todo`

**Context and decision-making:**

- `intro`, `file`, `link`, `require`, `handoff`

**Operations:**

- `context`, `next-action`, `can`, `search`, `grep`, `symbols`, `deps`, `actor`, `view`, `serve`

**Repair and inspection:**

- `lock`, `doctor`, `repair`, `reindex`

**Project lifecycle:**

- `init`, `status`, `export`, `import`, `snapshot`

## Install

```bash
python -m pip install -e .
python -m pip install -e ".[dev]"
```

## Quick start

Initialize durable state in the current workspace:

```bash
taskledger init
# or keep storage outside the source repo
taskledger init --taskledger-dir /mnt/cloud/taskledger/my-repo
# or point at another workspace explicitly
taskledger --root /path/to/repo init
```

`init` writes `taskledger.toml` in the workspace root. By default that config
points at `.taskledger/`, but `--taskledger-dir` can move durable state to an
external directory without nesting another `.taskledger` inside it.

Create and activate a task, ask required planning questions, regenerate the
plan from answers, approve it, implement todos with evidence, and validate it:

```bash
taskledger task create "Rewrite V2" --slug rewrite-v2 --description "Migrate to the task-first design."
taskledger task activate rewrite-v2 --reason "Start planning"
taskledger plan start
taskledger question add --text "Should exports include the new state?" --required-for-plan
taskledger question answer-many --text "q-0001: Yes."
taskledger question status
taskledger plan upsert --from-answers --file ./plan.md
taskledger plan lint --version 1
taskledger plan accept --version 1 --note "Ready."

taskledger next-action
taskledger --json next-action

taskledger context --for implementation --format markdown
taskledger implement start
taskledger implement checklist
taskledger implement change --path taskledger/storage/task_store.py --kind edit --summary "Normalized v2 markdown storage."
taskledger todo done todo-0001 --evidence "Updated taskledger/storage/task_store.py"
taskledger implement finish --summary "Implemented the approved plan."

taskledger context --for validation --format markdown
taskledger validate start
taskledger validate status
taskledger validate check --criterion ac-0001 --status pass --evidence "pytest -q tests/test_taskledger_v2_cli.py"
taskledger validate finish --result passed --summary "Validated the rewrite."
```

`taskledger next-action` is the preferred fresh-context entrypoint. It stays
read-only and points at the next concrete question, todo, criterion, or repair
step.

Human output example:

```text
todo-work: Implementation is in progress; 1 todos remain.
Next todo: todo-0001 -- Update next-action JSON payload.
Command: taskledger todo show todo-0001
Mark todo done after evidence exists: taskledger todo done todo-0001 --evidence "..."
Progress: 0/1 todos done
```

JSON result example:

```json
{
  "kind": "task_next_action",
  "action": "todo-work",
  "next_command": "taskledger todo show todo-0001",
  "next_item": {
    "kind": "todo",
    "id": "todo-0001",
    "text": "Update next-action JSON payload."
  },
  "commands": [
    {
      "kind": "inspect",
      "label": "Show next todo",
      "command": "taskledger todo show todo-0001",
      "primary": true
    }
  ],
  "progress": {
    "todos": {
      "total": 1,
      "done": 0,
      "open": 1,
      "open_ids": ["todo-0001"]
    }
  },
  "blocking": []
}
```

## Human monitoring UI

`taskledger serve` starts a read-only local dashboard for humans monitoring task
state. The MVP binds to localhost only, refreshes with read-only JSON polling,
and exposes no browser mutation endpoints.

```bash
taskledger serve
taskledger serve --open
taskledger serve --task rewrite-v2 --refresh-ms 2000
```

Agents should keep using `taskledger next-action`, `taskledger context`, and
`--json` commands as the canonical automation interface.

## Storage layout

`taskledger` keeps project-local configuration in the workspace root and durable
records under the configured storage root:

```text
taskledger.toml
.taskledger/
  intros/
  tasks/
  events/
  indexes/   # optional derived caches and registries
```

Markdown files are canonical. Task, plan, and run listings scan those records
directly. JSON files under `.taskledger/indexes/` are optional derived caches or
registries and are not required for task correctness.

You can also point `taskledger.toml` at an external storage root:

```bash
taskledger init --taskledger-dir /mnt/cloud/taskledger/project-a
```

```text
/home/me/src/project-a/taskledger.toml
/mnt/cloud/taskledger/project-a/storage.yaml
/mnt/cloud/taskledger/project-a/tasks/
/mnt/cloud/taskledger/project-a/events/
/mnt/cloud/taskledger/project-a/indexes/
```

Use one `taskledger_dir` per source project. Do not share one storage directory
across unrelated repositories.

## JSON output

Use `--json` for machine-readable payloads:

```bash
taskledger --json status --full
taskledger --json task active
taskledger --json task show
taskledger --json context --for validation --format json
```

Example status payload:

```json
{
  "ok": true,
  "command": "status",
  "result": {
    "kind": "taskledger_status",
    "workspace_root": "/home/me/src/project-a",
    "config_path": "/home/me/src/project-a/taskledger.toml",
    "taskledger_dir": "/home/me/src/project-a/.taskledger",
    "project_dir": "/home/me/src/project-a/.taskledger",
    "counts": {
      "tasks": 1,
      "introductions": 0,
      "plans": 1,
      "questions": 1,
      "runs": 2,
      "changes": 1,
      "locks": 0
    },
    "active_task": null,
    "healthy": true
  },
  "events": []
}
```

## Handoff-driven work

Fresh-context handoff is a primary feature:

```bash
taskledger context --for planning --format markdown
taskledger context --for implementation --format markdown
taskledger context --for validation --format json
taskledger task dossier --format markdown
taskledger handoff create --mode implementation --intended-actor agent --intended-harness codex
taskledger handoff claim handoff-0001
taskledger handoff close handoff-0001 --reason "Implementation started."
```

## Fresh-worker contexts

Use focused contexts when handing one todo or one review run to a fresh worker:

```bash
taskledger context --for implementer --todo todo-0003
taskledger context --for spec-reviewer --run run-0008
taskledger context --for code-reviewer --run run-0008
taskledger handoff create --mode implementation --todo todo-0003
taskledger handoff show handoff-0001 --format markdown
```

`handoff create` now stores the generated Markdown context snapshot in the handoff
record so another harness can continue from the exact same input.

## Multi-Actor Handoff Protocol

The handoff protocol enables safe work transitions between human and agent actors across different harnesses:

### Features

- **Actor Identity**: Track WHO performs each stage (human, agent, system)
- **Harness Tracking**: Record FROM WHERE each stage ran (manual, Codex, OpenCode, etc.)
- **Handoff Records**: Explicitly hand off work with context and intent
- **Claim Protocol**: New actors claim handoffs before starting work
- **Lock Management**: Transfer or release locks during handoffs
- **Event Trail**: Full audit trail recording all state changes
- **Durable Records**: Markdown-first storage with YAML metadata

### Quick Start

```bash
# See your current identity
$ taskledger actor whoami

# Create a handoff
$ taskledger handoff create --task task-0001 --mode implementation --todo todo-0003

# Claim it
$ taskledger handoff claim handoff-0001 --task task-0001

# Show details
$ taskledger handoff show handoff-0001 --task task-0001 --format text

# Close when done
$ taskledger handoff close handoff-0001 --task task-0001 --reason "Continued."
```

See [docs/usage.rst](docs/usage.rst) and
[skills/taskledger/examples/validation-flow.md](skills/taskledger/examples/validation-flow.md)
for task-first handoff examples.

## Export, import, and snapshots

```bash
taskledger --json export
taskledger import ./taskledger-export.json --replace
taskledger snapshot ./artifacts
```

## Skill packaging

The packaged skill lives at:

```text
skills/taskledger/SKILL.md
```

It includes example planner, implementer, and validator handoffs under
`skills/taskledger/examples/`.

## Development

```bash
pytest -q
ruff check .
```
