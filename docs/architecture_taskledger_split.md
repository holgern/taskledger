# Taskledger split architecture

`taskledger` owns durable project state only: models, storage, context composition, search/import/export, and persisted run/validation records. `runtildone` owns runtime-only concerns such as CLI option parsing, preview/execute calls, live rendering, stage orchestration (`plan`/`implement`/`validate`), and loop/runtime adapters.

## Boundary rules

- `taskledger` must not import `runtildone.runtime.*`, `runtildone.supervisor`, `runtildone.rendering.*`, or `runtildone.loops.*`.
- `taskledger` must not contain runtime command strings, runtime artifact layout assumptions, or runtime invocation contracts.
- `runtildone.integrations.taskledger_runtime` maps `CLIOptions` and runtime preview/result payloads into execution requests and persisted taskledger records.
- `runtildone.projects.*` remains importable as the compatibility surface and should stay thin.

## Current split

- `taskledger/models/` is the canonical project-core model layer.
- `taskledger/storage/` is the canonical project-state storage layer.
- `taskledger/api/` exposes state CRUD/query operations only.
- `runtildone/integrations/taskledger_runtime/services.py` owns project run preparation/execution semantics.
- `runtildone/runtime/stage_flows.py` owns item-stage orchestration.
- `runtildone/projects/runner.py` is a compatibility wrapper over runtime-owned services.
- `runtildone/integrations/taskledger_runtime/` owns the runtime adapter boundary.

## Guardrails

- Keep `runtildone.projects.runner.build_preview` and `run_once` monkeypatchable.
- Preserve project preview/result payload shape through the adapter layer.
- Ship `taskledger` from the same distribution until packaging is split
  further.
