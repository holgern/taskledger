# taskledger API contract for runtildone

This file defines the official boundary that `runtildone` should use.

## 1. Import boundary

### Allowed imports

- `taskledger.errors`
- `taskledger.api.contexts`
- `taskledger.api.items`
- `taskledger.api.memories`
- `taskledger.api.repos`
- `taskledger.api.runs`
- `taskledger.api.validation`
- `taskledger.api.composition`
- `taskledger.api.execution_requests`
- `taskledger.api.runtime_support`
- `taskledger.api.types`
- `taskledger.api.workflows`

### Forbidden imports from runtildone

- `taskledger.storage`
- `taskledger.storage.*`
- `taskledger.context`
- `taskledger.compose`
- `taskledger.models`
- `taskledger.models.execution`
- `taskledger.links`
- `taskledger.search`

If a needed capability is missing, add it under `taskledger.api.*` instead of importing internals.

### Taskledger-local APIs (not in runtildone boundary)

These APIs are stable for the `taskledger` package and CLI internals, but are not part
of the runtildone import boundary above:

- `taskledger.api.project`
- `taskledger.api.search`

## 2. Global API rule

All public CRUD/runtime-composition functions use:

- `workspace_root: Path` as the first argument

Do not pass internal `ProjectPaths` objects across the boundary.

## 3. Canonical error imports

```python
from taskledger.errors import (
    TaskledgerError,
    LaunchError,
    InvalidPromptError,
    UnsupportedAgentError,
    AgentNotInstalledError,
)
```

## 4. Canonical DTO imports

Use only `taskledger.api.types`:

```python
from taskledger.api.types import (
    ContextEntry,
    WorkItem,
    Memory,
    Repo,
    RunRecord,
    ValidationRecord,
    ProjectConfig,
    SourceBudget,
    ExpandedSelection,
    ContextSource,
    ComposedBundle,
    ExecutionOptions,
    ExecutionPreviewRecord,
    ExecutionOutcomeRecord,
    ExecutionStatus,
    WorkflowDefinition,
    WorkflowStageDefinition,
    WorkflowTransition,
    ItemWorkflowState,
    ItemStageRecord,
    ExecutionRequest,
    ExpandedExecutionRequest,
)
```

## 5. Option B split contract

This repository intentionally uses **Option B — split contract**.

### CLI + Python

- `taskledger.api.contexts`
- `taskledger.api.items`
- `taskledger.api.memories`
- `taskledger.api.repos`
- `taskledger.api.runs`
- `taskledger.api.validation`
- `taskledger.api.workflows`

### Extended CLI + Python

- `taskledger.api.execution_requests`
- `taskledger.api.composition`
- `taskledger.api.runtime_support`

Notes:

- These modules are stable public APIs.
- They also have dedicated CLI groups: `exec-request`, `compose`, and `runtime-support`.

## 6. Entity APIs

### Contexts (`taskledger.api.contexts`)

Canonical functions:

- `save_context`
- `list_contexts`
- `resolve_context`
- `rename_context`
- `delete_context`

### Items (`taskledger.api.items`)

Canonical functions:

- `create_item`
- `list_items`
- `show_item`
- `update_item`
- `approve_item`
- `reopen_item`
- `close_item`
- `item_memory_refs`
- `resolve_item_memory`
- `read_item_memory_body`
- `write_item_memory_body`
- `rename_item_memory`
- `retag_item_memory`
- `delete_item_memory`
- `next_action_payload`

### Memories (`taskledger.api.memories`)

Canonical functions:

- `create_memory`
- `list_memories`
- `resolve_memory`
- `read_memory_body`
- `refresh_memory`
- `rename_memory`
- `write_memory_body`
- `update_memory_body`
- `update_memory_tags`
- `delete_memory`

### Repos (`taskledger.api.repos`)

Canonical functions:

- `add_repo`
- `list_repos`
- `resolve_repo`
- `resolve_repo_root`
- `set_repo_role`
- `set_default_execution_repo`
- `clear_default_execution_repo`
- `remove_repo`

### Runs (`taskledger.api.runs`)

Canonical functions:

- `list_runs`
- `show_run`
- `delete_run`
- `cleanup_runs`
- `promote_run_output`
- `promote_run_report`

### Validation (`taskledger.api.validation`)

Canonical functions:

- `list_validation_records`
- `append_validation_record`
- `remove_validation_records`

### Workflows (`taskledger.api.workflows`)

Canonical functions:

- `list_workflows`
- `resolve_workflow`
- `save_workflow_definition`
- `delete_workflow_definition`
- `default_workflow_id`
- `set_default_workflow`
- `assign_item_workflow`
- `item_workflow_state`
- `item_stage_records`
- `latest_stage_record`
- `allowed_stage_transitions`
- `can_enter_stage`
- `enter_stage`
- `mark_stage_running`
- `mark_stage_succeeded`
- `mark_stage_failed`
- `mark_stage_needs_review`
- `approve_stage`

Notes:

- Workflow definitions are runner-agnostic durable semantics.
- Stage history is durable and separate from generic run records.
- Existing `.taskledger/project.toml` artifact rules remain readable as a
  compatibility path for `taskledger next` / `report` / `doctor`, but new
  workflow ownership lives in workflow APIs and stage records.

### Execution requests (`taskledger.api.execution_requests`)

Canonical functions:

- `build_execution_request`
- `expand_execution_request`
- `record_execution_outcome`

Notes:

- These APIs build and expand workflow-owned execution contracts.
- They must not launch a harness or encode provider-specific subprocess logic.
- `record_execution_outcome(...)` updates durable workflow state after a runner
  finishes.

## 7. Composition API (`taskledger.api.composition`)

```python
from taskledger.api.composition import (
    SelectionRequest,
    expand_selection,
    build_sources,
    compose_bundle,
    describe_sources,
    repo_refs_for_sources,
    build_compose_payload,
)
```

Notes:

- `taskledger.api.compose` is removed. Use `taskledger.api.composition`.
- `SourceBudget`, `ExpandedSelection`, `ContextSource`, and `ComposedBundle` are available from `taskledger.api.types` and re-exported in this module.

Minimal flow:

```python
request = SelectionRequest(context_names=("my-context",), memory_refs=("mem-0001",))
expanded = expand_selection(workspace_root, request)
sources = build_sources(
    workspace_root,
    expanded,
    default_context_order=("memory", "file", "item", "inline", "loop_artifact"),
    source_budget=SourceBudget(max_source_chars=12000, max_total_chars=48000),
)
bundle = compose_bundle(prompt=user_prompt, sources=sources)
payload = build_compose_payload(
    context_name="my-context",
    prompt=user_prompt,
    explicit_inputs={
        "context_inputs": request.context_names,
        "memory_inputs": request.memory_refs,
        "file_inputs": request.file_refs,
        "item_inputs": request.item_refs,
        "inline_inputs": request.inline_texts,
        "loop_artifact_inputs": request.loop_latest_refs,
    },
    selected_repo_refs=repo_refs_for_sources(sources),
    run_in_repo=None,
    source_budget=SourceBudget(max_source_chars=12000, max_total_chars=48000),
    bundle=bundle,
)
```

## 8. Execution-request flow (`taskledger.api.execution_requests`)

```python
from taskledger.api.execution_requests import (
    build_execution_request,
    expand_execution_request,
    record_execution_outcome,
)
```

Typical flow:

```python
request = build_execution_request(
    workspace_root,
    item_ref="item-0001",
    stage_id="plan",
    inline_texts=("Focus on repository-safe changes.",),
)
expanded = expand_execution_request(workspace_root, request=request)
# runner executes expanded.final_prompt elsewhere
# runner then reports the durable outcome:
# record_execution_outcome(workspace_root, request=request, outcome=outcome)
```

## 9. Runtime support API (`taskledger.api.runtime_support`)

```python
from taskledger.api.runtime_support import (
    RunArtifactPaths,
    get_effective_project_config,
    create_run_artifact_layout,
    save_run_record,
    resolve_repo_root,
)
```

Typical flow:

```python
config = get_effective_project_config(workspace_root)
layout = create_run_artifact_layout(workspace_root, origin="runtime")
# runtime writes outputs into layout.run_dir
save_run_record(workspace_root, run_record)
repo_root = resolve_repo_root(workspace_root, "main-repo")
```

## 10. Migration notes for runtildone

- Replace all `taskledger.context` and `taskledger.compose` usage with `taskledger.api.composition`.
- Replace hardcoded stage semantics with `taskledger.api.workflows` and `taskledger.api.execution_requests`.
- Replace all `taskledger.storage*` usage with `taskledger.api.*` and `taskledger.api.runtime_support`.
- Replace all `taskledger.models*` DTO imports with `taskledger.api.types`.
- Keep compatibility wrappers thin and forwarding only; no new persistence logic in wrappers.
