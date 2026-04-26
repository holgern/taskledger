# taskledger

`taskledger` is a task-first durable state layer for staged coding work. It stores
plans, approval state, implementation logs, validation results, locks, and
fresh-context handoffs under `.taskledger/`.

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
- `context`, `next-action`, `can`, `search`, `grep`, `symbols`, `deps`, `actor`, `view`

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
# or point at another workspace explicitly
taskledger --root /path/to/repo init
```

Create and activate a task, ask required planning questions, regenerate the
plan from answers, approve it, implement todos with evidence, and validate it:

```bash
taskledger task create "Rewrite V2" --slug rewrite-v2 --description "Migrate to the task-first design."
taskledger task activate rewrite-v2 --reason "Start planning"
taskledger plan start
taskledger question add --text "Should exports include the new state?" --required-for-plan
taskledger question answer q-0001 --text "Yes."
taskledger question status
taskledger plan regenerate --from-answers --file ./plan.md
taskledger plan approve --version 1 --actor user --note "Ready."

taskledger context --for implementation --format markdown
taskledger implement start
taskledger implement checklist
taskledger implement change --path taskledger/storage/v2.py --kind edit --summary "Normalized v2 markdown storage."
taskledger todo done todo-0001 --evidence "Updated taskledger/storage/v2.py"
taskledger implement finish --summary "Implemented the approved plan."

taskledger context --for validation --format markdown
taskledger validate start
taskledger validate status
taskledger validate check --criterion ac-0001 --status pass --evidence "pytest -q tests/test_taskledger_v2_cli.py"
taskledger validate finish --result passed --summary "Validated the rewrite."
```

## Storage layout

`taskledger` keeps durable records under `.taskledger/`:

```text
.taskledger/
  intros/
  tasks/
  events/
  indexes/
```

Markdown files are canonical. JSON indexes are rebuildable caches.

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
$ taskledger handoff create --task task-0001 --mode implementation

# Claim it
$ taskledger handoff claim handoff-0001 --task task-0001

# Show details
$ taskledger handoff show handoff-0001 --task task-0001

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
