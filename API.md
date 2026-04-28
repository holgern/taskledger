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
- `show_active_task`
- `activate_task`
- `deactivate_task`
- `clear_active_task`
- `resolve_active_task`
- `list_task_summaries`
- `show_task`
- `edit_task`
- `cancel_task`
- `close_task`
- `add_requirement`
- `remove_requirement`
- `waive_requirement`
- `add_file_link`
- `remove_file_link`
- `list_file_links`
- `add_todo`
- `set_todo_done`
- `show_todo`
- `todo_status`
- `next_todo`
- `task_dossier`
- `next_action`
- `can_perform`
- `reindex`
- `repair_task_record`

### `taskledger.api.plans`

- `start_planning`
- `propose_plan`
- `upsert_plan`
- `regenerate_plan_from_answers`
- `materialize_plan_todos`
- `list_plan_versions`
- `show_plan`
- `diff_plan`
- `lint_plan`
- `approve_plan`
- `reject_plan`
- `revise_plan`
- `run_planning_command`

### `taskledger.api.questions`

- `add_question`
- `list_questions`
- `list_open_questions`
- `answer_question`
- `answer_questions`
- `dismiss_question`
- `question_status`

### `taskledger.api.task_runs`

- `start_implementation`
- `log_implementation`
- `add_implementation_deviation`
- `add_implementation_artifact`
- `add_change`
- `scan_changes`
- `run_implementation_command`
- `finish_implementation`
- `show_task_run`
- `start_validation`
- `add_validation_check`
- `validation_status`
- `waive_criterion`
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
- `create_handoff`
- `list_all_handoffs`
- `show_handoff`
- `claim_handoff_api`
- `close_handoff_api`
- `cancel_handoff_api`

Current focused-context signatures:

```python
render_handoff(
    workspace_root: Path,
    task_ref: str,
    *,
    mode: str | None = None,
    context_for: str | None = None,
    scope: str | None = None,
    todo_id: str | None = None,
    focus_run_id: str | None = None,
    format_name: str = "markdown",
) -> str | dict[str, object]

create_handoff(
    workspace_root: Path,
    task_ref: str,
    *,
    mode: str,
    context_for: str | None = None,
    scope: str | None = None,
    todo_id: str | None = None,
    focus_run_id: str | None = None,
    intended_actor_type: str | None = None,
    intended_actor_name: str | None = None,
    intended_harness: str | None = None,
    summary: str | None = None,
    next_action: str | None = None,
    actor: ActorRef | None = None,
    harness: HarnessRef | None = None,
) -> dict[str, object]
```

Focused handoffs store the generated Markdown context snapshot in the handoff
record body and return compact metadata, including `context_hash` and
`context_path`.

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
- `link`
- `require`
- `lock`
- `context`
- `handoff`
- `repair`
- `doctor`

Top-level commands that are part of the supported surface are:

- `init`
- `status`
- `serve`
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

Workflow additions:

- `task create` creates a task. Use `task activate TASK_REF` to make it active.
- `plan draft`, `plan upsert --from-answers`, and
  `plan materialize-todos` support the question-answer-regenerate loop.
- `question status` reports required open questions and whether regeneration is
  needed.
- `todo done` records evidence with `--evidence`, `--artifact`, and `--change`.
- `handoff create|list|show|claim|close|cancel` are available on the main
  task-first handoff command group.
- `serve` is a human-oriented, read-only localhost dashboard. Agents should keep
  using `next-action`, `context`, `view`, and JSON commands for automation.
