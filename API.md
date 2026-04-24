# taskledger API contract

This repository exposes a task-first public API. The supported modules are:

- `taskledger.errors`
- `taskledger.api.project`
- `taskledger.api.tasks`
- `taskledger.api.plans`
- `taskledger.api.questions`
- `taskledger.api.task_runs`
- `taskledger.api.introductions`
- `taskledger.api.locks`
- `taskledger.api.handoff`
- `taskledger.api.search`

## Import boundary

Consumers must not import from:

- `taskledger.storage`
- `taskledger.storage.*`
- `taskledger.services`
- `taskledger.domain`
- `taskledger.search`

If a capability is missing, add it under `taskledger.api.*`.

## Global rule

All workspace-bound public entrypoints accept `workspace_root: Path` as the first
argument.

## Canonical errors

```python
from taskledger.errors import (
    TaskledgerError,
    LaunchError,
    InvalidPromptError,
    UnsupportedAgentError,
    AgentNotInstalledError,
)
```

## Public modules

### `taskledger.api.project`

- `init_project`
- `project_status`
- `project_status_summary`
- `project_doctor`
- `project_export`
- `project_import`
- `project_snapshot`

### `taskledger.api.tasks`

- `create_task`
- `list_task_summaries`
- `show_task`
- `edit_task`
- `cancel_task`
- `close_task`
- `add_requirement`
- `remove_requirement`
- `add_file_link`
- `remove_file_link`
- `list_file_links`
- `add_todo`
- `set_todo_done`
- `show_todo`
- `next_action`
- `can_perform`
- `reindex`

### `taskledger.api.plans`

- `start_planning`
- `propose_plan`
- `list_plan_versions`
- `show_plan`
- `diff_plan`
- `approve_plan`
- `reject_plan`
- `revise_plan`

### `taskledger.api.questions`

- `add_question`
- `list_questions`
- `list_open_questions`
- `answer_question`
- `dismiss_question`

### `taskledger.api.task_runs`

- `start_implementation`
- `log_implementation`
- `add_implementation_deviation`
- `add_implementation_artifact`
- `add_change`
- `finish_implementation`
- `show_task_run`
- `start_validation`
- `add_validation_check`
- `finish_validation`
- `list_runs`
- `list_changes`

### `taskledger.api.introductions`

- `create_introduction`
- `list_introductions`
- `resolve_introduction`
- `link_introduction`

### `taskledger.api.locks`

- `show_lock`
- `break_lock`
- `list_locks`
- `load_active_locks`

### `taskledger.api.handoff`

- `render_handoff`

### `taskledger.api.search`

- `search_workspace`
- `grep_workspace`
- `symbols_workspace`
- `dependencies_for_module`

## CLI command groups

The public task-first CLI surface is organized around these command groups:

- `task`
- `plan`
- `question`
- `implement`
- `validate`
- `todo`
- `intro`
- `file`
- `require`
- `lock`
- `handoff`
- `doctor`

Top-level commands that are part of the supported surface are:

- `init`
- `status`
- `next-action`
- `can`
- `reindex`
- `export`
- `import`
- `snapshot`
- `search`
- `grep`
- `symbols`
- `deps`

All CLI commands support `--cwd`; task-first workflows also support `--root` as
the preferred workspace alias. JSON mode returns a stable envelope with
`ok`, `command`, `task_id` when applicable, `result`, `events`, and a
structured `error` object on failure.
