# Public Surface

`taskledger` supports the task-first workflow:

```text
task -> plan -> approval -> implement -> validate -> done
```

## Supported CLI Groups

- `task`, `plan`, `question`, `implement`, `validate`, `todo`
- `intro`, `file`, `link`, `require`, `lock`, `handoff`
- `doctor`, `repair`, `next-action`, `can`, `reindex`
- `init`, `status`, `export`, `import`, `snapshot`
- `context`, `search`, `grep`, `symbols`, `deps`

### question subcommands

- `question add`, `question list [--status STATUS]`, `question answers [--format markdown|json]`
- `question answer`, `question dismiss`, `question open`, `question status`

## Supported Python API Modules

- `taskledger.api.project`
- `taskledger.api.tasks`
- `taskledger.api.plans`
- `taskledger.api.questions`
- `taskledger.api.task_runs`
- `taskledger.api.introductions`
- `taskledger.api.locks`
- `taskledger.api.handoff`
- `taskledger.api.search`

## Removed Legacy Surfaces

The old item/memory/repo/run/workflow/context/compose execution surfaces are not
part of the public compatibility contract. The corresponding CLI groups and
Python API modules have been removed rather than migrated.
