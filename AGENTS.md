# AGENTS.md

This file defines how coding agents should work in the `taskledger` repository.

## 1. Project identity

`taskledger` is the durable project-state layer extracted from the older `runtildone` project surface.

It owns:

- persistent project data under `.taskledger/`
- typed project models
- storage and validation helpers
- context/source expansion and composition
- project inspection and doctor checks
- import/export/snapshot helpers
- repository search and dependency inspection
- a Typer CLI for state inspection and CRUD-style updates

It does **not** own runtime execution orchestration, harness launching, or live agent-loop process control.

## 2. Core architecture

Prefer edits in the correct layer.

- `taskledger/models/` — canonical durable data model and serialization
- `taskledger/storage/` — filesystem layout, persistence, normalization, cross-record invariants
- `taskledger/api/` — workspace-root convenience wrappers over storage
- `taskledger/context.py` — context expansion, source material construction, loop artifact resolution, source budgeting
- `taskledger/compose.py` — project compose payload generation and explanations
- `taskledger/doctor.py` / `taskledger/links.py` — integrity inspection and broken-link detection
- `taskledger/search.py` — repo file discovery, grep/symbol/dependency helpers
- `taskledger/cli*.py` — Typer command wiring and presentation only
- `docs/` — Sphinx documentation and user-facing examples
- `tests/` — regression coverage

Do not put reusable behavior in CLI modules when the owning logic belongs in `storage/`, `api/`, `context.py`, `compose.py`, or `doctor.py`.

## 3. Stability-sensitive contracts

Preserve these unless the task explicitly requires a change.

### 3.1 Filesystem layout

`taskledger` persists state under `.taskledger/`, not legacy `.runtildone/project/`.

Treat these paths as compatibility-sensitive:

- `.taskledger/project.toml`
- `.taskledger/repos/index.json`
- `.taskledger/memories/<memory_id>.md`
- `.taskledger/contexts/index.json`
- `.taskledger/items/<item_id>.md`
- `.taskledger/runs/<run_id>/record.json`
- `.taskledger/validation/records.json`

### 3.2 Public Python surface

Preserve behavior and meanings for:

- `taskledger.api.project.*`
- `taskledger.api.items.*`
- `taskledger.api.memories.*`
- `taskledger.api.contexts.*`
- `taskledger.api.repos.*`
- `taskledger.api.runs.*`
- `taskledger.api.search.*`
- `taskledger.api.validation.*`
- `taskledger.api.workflows.*`
- `taskledger.api.execution_requests.*`
- `taskledger.api.composition.*`
- `taskledger.api.runtime_support.*`
- dataclass `to_dict()` / `from_dict()` contracts in `taskledger.models`

### 3.3 CLI surface

Treat the current command tree as stable:

- top-level: `init`, `status`, `board`, `next`, `doctor`, `report`, `export`, `import`, `snapshot`, `search`, `grep`, `symbols`, `deps`
- subcommands: `item`, `memory`, `context`, `repo`, `runs`, `validation`, `workflow`
- global options: `--cwd`, `--json`

Option B split contract is intentional:

- `execution_requests`, `composition`, and `runtime_support` are Python-only APIs.
- Missing CLI groups for those modules are expected unless explicitly requested.

When changing CLI behavior:

- preserve JSON output shape where practical
- preserve exit-code meaning
- keep human output concise and machine output complete
- update help strings in the same patch
- add CLI tests for both success and failure paths when relevant

## 4. Boundary rules

`taskledger` is the durable-state side of the split.

Do not introduce:

- imports from runtime-only `runtildone` modules into `taskledger/`
- runtime command strings or harness-specific execution logic in `taskledger/`
- assumptions that loop artifacts live in a runtime-owned fixed layout unless that reference is already part of a durable persisted contract
- docs that require `runtildone` just to build `taskledger` docs

The compatibility boundary belongs outside `taskledger`.

## 5. Working style

### 5.1 Prefer the smallest correct change

Default to the narrowest change that fixes the actual issue.

Priorities:

1. correctness
2. preserved durable-state contracts
3. explicit invariants
4. focused tests
5. documentation that matches behavior

Avoid:

- speculative abstractions
- broad refactors during feature work
- changing stored payload shapes casually
- moving behavior into CLI-only wrappers
- hidden migration logic without tests
- unrelated style churn

### 5.2 Fix the owning layer, then wire outward

Examples:

- persistence bug -> `taskledger/storage/*`
- workspace-root convenience bug -> `taskledger/api/*`
- source expansion or loop artifact issue -> `taskledger/context.py`
- integrity-report issue -> `taskledger/doctor.py` or `taskledger/links.py`
- CLI rendering/help issue -> `taskledger/cli*.py`
- docs mismatch -> `docs/*` and possibly `README.md`

## 6. Durable model rules

The most important model types are in `taskledger/models/core.py`.

Be careful with:

- `ProjectRepo`
- `ProjectMemory`
- `ProjectContextEntry`
- `ProjectWorkItem`
- `ContextSource`
- `ContextBundle`
- `ProjectRunRecord`
- `ProjectState`

Do not casually rename or remove serialized fields such as:

- `preferred_for_execution`
- `loop_latest_refs`
- `analysis_memory_ref`
- `state_memory_ref`
- `plan_memory_ref`
- `implementation_memory_ref`
- `validation_memory_ref`
- `linked_memories`
- `linked_runs`
- `linked_loop_tasks`
- `save_target_ref`
- `acceptance_criteria`
- `validation_checklist`
- `labels`
- `depends_on`

If a task changes serialization, call it out explicitly and add round-trip tests.

## 7. Loop and project rules

Loop-related durable references are already part of the project model.

Be careful with:

- `loop_latest_refs` stored on contexts
- `linked_loop_tasks` stored on work items
- loop artifact expansion in `taskledger/context.py`
- broken-link validation in `taskledger/doctor.py` and `taskledger/links.py`

When improving loop/project support:

- prefer durable references over runtime guesses
- make missing-loop diagnostics explicit
- test both valid and broken artifact references
- document how loop artifacts are referenced and surfaced

## 8. Search and repo rules

Search-related behavior should stay deterministic and repo-scoped.

Preserve semantics for:

- `search_workspace`
- `grep_workspace`
- `symbols_workspace`
- `dependencies_for_module`
- repo role validation (`read`, `write`, `both`)
- default execution repo rules

Do not weaken repo-path validation or default-execution safeguards without tests.

## 9. Doctor and integrity rules

`doctor` is a high-signal command. Keep its output grounded in persisted state.

Preserve or improve checks for:

- missing taskledger root files
- missing repo directories
- missing memory markdown files
- empty memories
- broken context references
- broken work-item links
- orphan run directories

If you add a new durable relation, update doctor/link checks and tests in the same change.

## 10. Documentation rules

Docs should describe `taskledger` as a standalone durable-state package.

When editing docs:

- keep `README.md` useful for first-time readers
- keep Sphinx docs buildable without importing unrelated runtime packages
- include concrete CLI examples
- show at least one JSON example when documenting machine-readable output
- document loop/project terminology where it appears in the model
- keep API docs aligned with the actual public wrappers in `taskledger.api`

## 11. Testing expectations

Every non-trivial behavior change needs verification.

Prefer the narrowest useful tests first.

### 11.1 Highest-value test areas

- storage round-trips for models and markdown/index persistence
- CLI success and failure cases
- import/export/snapshot behavior
- doctor diagnostics and broken-link detection
- context expansion and loop artifact handling
- repo role / default execution repo rules
- memory update modes (`replace`, `append`, `prepend`)
- run promotion and cleanup helpers
- validation record normalization and summaries

### 11.2 Current gaps worth filling

When the task touches these areas, add focused tests because coverage is still thin:

- context rename/delete CLI
- memory rename/delete/retag/prepend CLI
- repo remove/role/default CLI
- runs delete/cleanup/promote CLI
- validation CLI or validation API coverage
- loop artifact expansion and broken loop references
- project export/import/snapshot round-trips
- doctor warning/error details
- docs config independence from `runtildone`

### 11.3 Preferred commands

```bash
python -m pip install -e .
python -m pip install -e ".[dev]"

pytest -q
pytest tests/test_taskledger_cli.py -q
pytest tests/test_taskledger_storage_roots.py -q
pytest tests/test_taskledger_boundaries.py -q

ruff check .
ruff format .
```

Start targeted. Run the full suite when a change crosses layers.

## 12. What good agent work looks like here

A strong change in this repo usually:

- edits the owning layer
- preserves `.taskledger/` durability rules
- keeps runtime-only logic out of `taskledger`
- improves CLI/API parity rather than adding one-off workarounds
- expands tests near the changed behavior
- updates docs/examples in the same patch when user-visible behavior changes
- keeps diffs small unless a larger redesign is clearly required

## 13. What to avoid

- copying `runtildone` agent guidance into this repo
- adding runtime orchestration into durable-state modules
- changing serialized field names casually
- weakening doctor/link validation
- leaving API-only features undocumented and unreachable from the CLI without a reason
- broad refactors mixed into behavior work
- README/docs that lag behind the actual command surface
