# taskledger

`taskledger` is the standalone durable-state layer for coding work. It stores
project items, memories, contexts, repos, run records, validation records, and
workflow metadata under `.taskledger/` so tools can inspect and update project
state without owning runtime orchestration.

## What it does

- persists project state under `.taskledger/`
- exposes a typed Python API in `taskledger.api.*`
- provides a Typer CLI for inspection and CRUD-style updates
- expands and composes context sources for downstream runtimes
- exports, imports, and snapshots project state
- checks integrity with `taskledger doctor`
- supports additive workflow metadata for dependency-aware reporting

`taskledger` does **not** run agent loops, launch harnesses, or own live runtime
execution control.

## Storage layout

`taskledger` stores durable state under `.taskledger/`.

- memories are stored as one Markdown document per memory:
  `.taskledger/memories/<id>.md`
- work items are stored as one Markdown document per item:
  `.taskledger/items/<id>.md`
- both item and memory YAML headers include a fixed `file_version` field
- repos, contexts, workflows, stages, and validation keep JSON index files

## Install

```bash
python -m pip install -e .
python -m pip install -e ".[dev]"
```

## Quick start

Initialize project state in the current workspace:

```bash
taskledger init
```

Create a work item, inspect it, and create supporting memories. Item role
memories are created lazily on the first meaningful write:

```bash
taskledger item create parser-fix --description "Repair parser handling."
taskledger item list
taskledger item show parser-fix
taskledger item view parser-fix
taskledger item knowledge parser-fix
taskledger item memory write parser-fix --role plan --text "1. Update parser tests"
taskledger item approve parser-fix

taskledger memory create "Parser analysis" --text "Current parser behavior."
taskledger memory prepend parser-analysis --text "Priority: high"
taskledger memory retag parser-analysis --add-tag analysis --add-tag parser
```

For file-to-item ingestion, use the external `taskingest` Python CLI. It handles
the file discovery and item creation step before `taskledger` takes over durable
state management.

Manage saved contexts, repos, runs, and validation records:

```bash
taskledger context save parser-context --memory parser-analysis --item parser-fix --dir tests/
taskledger context show ctx-1
taskledger context rename parser-context --new-name release-parser-context

taskledger repo add core --path /path/to/repo --role both
taskledger repo set-default core

taskledger runs list
taskledger validation summary
```

Task-first v2 workflow commands are also available alongside the legacy
item/memory surface:

```bash
taskledger task create rewrite-v2 --description "Migrate to the task-centric v2 design."
taskledger plan start rewrite-v2
taskledger plan propose rewrite-v2 --file ./plan.md
taskledger plan approve rewrite-v2 --version 1
taskledger implement start rewrite-v2
taskledger implement add-change rewrite-v2 --path taskledger/storage/v2.py --kind edit --summary "Added v2 storage."
taskledger implement finish rewrite-v2 --summary "Implemented v2 storage and CLI."
taskledger validate start rewrite-v2
taskledger validate add-check rewrite-v2 --name "pytest -q passes" --status pass
taskledger validate finish rewrite-v2 --result passed --summary "Validated the migration."
taskledger handoff validation-context rewrite-v2
```

Inspect machine-readable state:

```bash
taskledger --json status
taskledger --json report
taskledger --json export --include-bodies
```

`taskledger status` is intentionally compact. Use `--full` when you need the
expanded doctor, workflow, and next-action details.

Example status payload:

```json
{
  "kind": "taskledger_status",
  "counts": {
    "contexts": 1,
    "memories": 2,
    "repos": 1,
    "runs": 2,
    "validation_records": 1,
    "work_items": 1
  },
  "healthy": true
}
```

## CLI surface

Top-level commands:

- `init`, `status`, `board`, `next`, `doctor`, `report`
- `export`, `import`, `snapshot`
- `search`, `grep`, `symbols`, `deps`
- `item`, `memory`, `context`, `repo`, `runs`, `validation`, `workflow`
- `task`, `plan`, `question`, `implement`, `validate`, `todo`
- `intro`, `file`, `require`, `lock`, `handoff`, `next-action`, `can`, `reindex`
- `exec-request`, `compose`, `runtime-support`

Notable lifecycle commands:

- `taskledger context rename|delete`
- `taskledger memory rename|retag|prepend|delete`
- `taskledger repo remove|set-role|set-default|clear-default`
- `taskledger runs delete|cleanup|promote-output|promote-report|summary`
- `taskledger validation list|add|remove|summary`
- `taskledger workflow list|save|delete|default|set-default|show|assign|state|stages|records|latest|transitions|can-enter|enter|mark-running|mark-succeeded|mark-failed|mark-needs-review|approve-stage`
- `taskledger exec-request build|expand|record-outcome`
- `taskledger compose expand|bundle`
- `taskledger runtime-support config|run-layout|resolve-repo`
- `taskledger task create|list|show|edit|cancel|close`
- `taskledger plan start|propose|show|diff|approve|reject|revise`
- `taskledger question add|list|answer|dismiss`
- `taskledger implement start|log|add-change|finish`
- `taskledger validate start|add-check|finish`
- `taskledger todo add|list|done|undone`
- `taskledger intro create|list|show|link`
- `taskledger file link|unlink`
- `taskledger require add|list`
- `taskledger lock show|break`
- `taskledger handoff show|plan-context|implementation-context|validation-context`
- `taskledger doctor locks`

Item dossier and composition examples:

- `taskledger item view parser-fix --role plan --role implementation`
- `taskledger item dossier parser-fix --output ./parser-fix.md`
- `taskledger --json compose bundle --prompt "Plan this work" --item parser-fix --no-item-memories`
- `taskledger --json compose bundle --prompt "Fix failing tests" --file-mode reference --dir tests/ --file tests/test_file.py`

## Python API

Use only the public `taskledger.api.*` modules:

```python
from pathlib import Path

from taskledger.api.items import create_item
from taskledger.api.memories import create_memory
from taskledger.api.project import project_status

workspace_root = Path(".")
create_memory(workspace_root, name="Current state", body="Parser fails on x.")
create_item(workspace_root, slug="parser-fix", description="Repair parser handling.")
status = project_status(workspace_root)
print(status["counts"])
```

See `docs/api.rst` and `API.md` for the supported boundary.

`taskledger.api.project` and `taskledger.api.search` are stable for taskledger
internals and local integrations, but are outside the runtildone import
boundary documented in `API.md`.

## Workflow metadata

`taskledger` can store additive workflow metadata in `.taskledger/project.toml`
to make `taskledger next`, `taskledger report`, and `taskledger doctor`
dependency-aware without introducing a runtime workflow engine.

`taskledger` also exposes first-class workflow definitions, item workflow state,
stage history, and execution-request helpers through
`taskledger.api.workflows` and `taskledger.api.execution_requests`.

Example:

```toml
workflow_schema = "opsx-lite"
project_context = "Prioritize dependencies before execution."
default_artifact_order = ["analysis", "plan", "implementation", "validation"]

[artifact_rules.analysis]
memory_ref_field = "analysis_memory_ref"

[artifact_rules.plan]
depends_on = ["analysis"]
memory_ref_field = "plan_memory_ref"

[artifact_rules.implementation]
depends_on = ["plan"]
memory_ref_field = "implementation_memory_ref"
```

Artifact completion is inferred from the referenced memory body content, while
work-item `depends_on` links provide cross-item blocking.

## Development

Run the existing checks from the repository root:

```bash
pytest -q
ruff check .
```
