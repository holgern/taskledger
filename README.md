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

Create a work item, inspect it, and create supporting memories:

```bash
taskledger item create parser-fix --text "Repair parser handling."
taskledger item list
taskledger item show item-0001

taskledger memory create "Parser analysis" --text "Current parser behavior."
taskledger memory prepend parser-analysis --text "Priority: high"
taskledger memory retag parser-analysis --add-tag analysis --add-tag parser
```

Manage saved contexts, repos, runs, and validation records:

```bash
taskledger context save parser-context --memory mem-0001 --item item-0001
taskledger context rename parser-context --new-name release-parser-context

taskledger repo add core --path /path/to/repo --role both
taskledger repo set-default core

taskledger runs list
taskledger validation summary
```

Inspect machine-readable state:

```bash
taskledger --json status
taskledger --json report
taskledger --json export --include-bodies
```

Example status payload:

```json
{
  "kind": "taskledger_status",
  "counts": {
    "contexts": 1,
    "memories": 6,
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
- `item`, `memory`, `context`, `repo`, `runs`, `validation`

Notable lifecycle commands:

- `taskledger context rename|delete`
- `taskledger memory rename|retag|prepend|delete`
- `taskledger repo remove|set-role|set-default|clear-default`
- `taskledger runs delete|cleanup|promote-output|promote-report|summary`
- `taskledger validation list|add|remove|summary`

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

## Workflow metadata

`taskledger` can store additive workflow metadata in `.taskledger/project.toml`
to make `taskledger next`, `taskledger report`, and `taskledger doctor`
dependency-aware without introducing a runtime workflow engine.

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
