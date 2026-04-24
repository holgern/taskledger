# taskledger

`taskledger` is a task-first durable state layer for staged coding work. It stores
plans, approval state, implementation logs, validation results, locks, and
fresh-context handoffs under `.taskledger/`.

## Canonical workflow

```text
task -> plan -> approval -> implement -> validate -> done
```

The supported command surface is centered on:

- `task`, `plan`, `question`, `implement`, `validate`, `todo`
- `intro`, `link`, `require`, `lock`, `context`
- `doctor`, `next-action`, `can`, `reindex`
- `init`, `status`, `export`, `import`, `snapshot`
- `search`, `grep`, `symbols`, `deps`

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

Create a task, propose a plan, approve it, implement it, and validate it:

```bash
taskledger task create rewrite-v2 --title "Rewrite V2" --description "Migrate to the task-first design."
taskledger plan start rewrite-v2
taskledger question add rewrite-v2 --text "Should exports include the new state?"
taskledger question answer rewrite-v2 q-0001 --text "Yes."
taskledger plan propose rewrite-v2 --criterion "Accepted workflow is implemented." --file ./plan.md
taskledger plan approve rewrite-v2 --version 1

taskledger context rewrite-v2 --for implementation --format markdown
taskledger implement start rewrite-v2
taskledger implement log rewrite-v2 --message "Started wiring the new storage model."
taskledger implement change rewrite-v2 --path taskledger/storage/v2.py --kind edit --summary "Normalized v2 markdown storage."
taskledger implement finish rewrite-v2 --summary "Implemented the approved plan."

taskledger context rewrite-v2 --for validation --format markdown
taskledger validate start rewrite-v2
taskledger validate check rewrite-v2 --criterion ac-0001 --status pass --evidence "pytest -q tests/test_taskledger_v2_cli.py"
taskledger validate finish rewrite-v2 --result passed --summary "Validated the rewrite."
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
taskledger --json task show rewrite-v2
taskledger --json context rewrite-v2 --for validation --format json
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
    "healthy": true
  },
  "events": []
}
```

## Handoff-driven work

Fresh-context handoff is a primary feature:

```bash
taskledger context rewrite-v2 --for planning --format markdown
taskledger context rewrite-v2 --for implementation --format markdown
taskledger context rewrite-v2 --for validation --format json
taskledger task dossier rewrite-v2 --format markdown
```

## Export, import, and snapshots

```bash
taskledger --json export
taskledger import ./taskledger-export.json --replace
taskledger snapshot ./artifacts
```

## Skill packaging

The packaged skill lives at:

```text
taskledger/skills/taskledger/SKILL.md
```

It includes example planner, implementer, and validator handoffs under
`taskledger/skills/taskledger/examples/`.

## Development

```bash
pytest -q
ruff check .
```
