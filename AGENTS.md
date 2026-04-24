# AGENTS.md

`taskledger` is a task-first CLI and Python package for staged coding work.

## Product shape

The canonical workflow is:

```text
task -> plan -> approval -> implement -> validate -> done
```

The supported surface is:

- `task`, `plan`, `question`, `implement`, `validate`, `todo`
- `intro`, `file`, `link`, `require`, `lock`, `handoff`
- `doctor`, `repair`, `next-action`, `can`, `reindex`
- `init`, `status`, `export`, `import`, `snapshot`

## Storage rules

- state lives under `.taskledger/`
- markdown records are canonical
- JSON indexes are rebuildable caches
- active stages require visible lock files
- stale locks are never cleared silently

## Owning layers

- `taskledger/domain/` — lifecycle enums, policies, record models
- `taskledger/storage/v2.py` and `taskledger/storage/locks.py` — persistence and lock I/O
- `taskledger/services/tasks.py` — task lifecycle orchestration
- `taskledger/services/handoff.py` — handoff payloads and rendering
- `taskledger/services/doctor_v2.py` — integrity checks
- `taskledger/api/*` — public wrappers
- `taskledger/cli*.py` — command wiring only

## Working rules

- keep changes in the owning layer
- preserve explicit exit-code behavior
- add or update tests with behavior changes
- prefer v2 task-first commands in examples and docs
- do not add migration code for removed legacy surfaces
