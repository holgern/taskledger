API reference
=============

The public API is centered around the ``taskledger.api`` modules and the CLI.

Official API contract
---------------------

Only the modules listed below are in the runtildone import boundary. Consumers
must not import from ``taskledger.storage``, ``taskledger.context``,
``taskledger.compose``, ``taskledger.models``, ``taskledger.links``, or
``taskledger.search`` directly.

Runtildone boundary modules:

- ``taskledger.api.contexts``
- ``taskledger.api.items``
- ``taskledger.api.memories``
- ``taskledger.api.repos``
- ``taskledger.api.runs``
- ``taskledger.api.validation``
- ``taskledger.api.composition``
- ``taskledger.api.execution_requests``
- ``taskledger.api.runtime_support``
- ``taskledger.api.types``
- ``taskledger.api.workflows``

Taskledger-local stable APIs (not in runtildone boundary):

- ``taskledger.api.project``
- ``taskledger.api.search``

Split contract (Option B)
-------------------------

``taskledger`` intentionally uses a split contract for CLI exposure.

CLI + Python:

- ``contexts``
- ``items``
- ``memories``
- ``repos``
- ``runs``
- ``validation``
- ``workflows``

Extended CLI + Python:

- ``execution_requests``
- ``composition``
- ``runtime_support``

These modules are stable public APIs and are also exposed via dedicated CLI
groups: ``exec-request``, ``compose``, and ``runtime-support``.

Global rules
^^^^^^^^^^^^^

All public workspace-bound CRUD/runtime-composition entrypoints accept
``workspace_root: Path`` as their first argument.
Pure transformation helpers that operate on already-expanded inputs may omit
``workspace_root`` (for example ``compose_bundle``, ``describe_sources``,
``repo_refs_for_sources``, and ``build_compose_payload`` in
``taskledger.api.composition``).
Internal ``ProjectPaths`` objects must not cross the boundary.

Errors
^^^^^^

.. code-block:: python

   from taskledger.errors import (
       TaskledgerError,
       LaunchError,
       InvalidPromptError,
       UnsupportedAgentError,
       AgentNotInstalledError,
   )

DTOs
^^^^

Use only ``taskledger.api.types`` for data-transfer objects:

.. code-block:: python

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
       ItemDossier,
       ItemDossierSection,
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

Entity modules
^^^^^^^^^^^^^^

Contexts (``taskledger.api.contexts``):

- ``save_context``
- ``list_contexts``
- ``resolve_context``
- ``rename_context``
- ``delete_context``
- ``build_context_for_item``

Items (``taskledger.api.items``):

- ``create_item``
- ``list_items``
- ``show_item``
- ``update_item``
- ``approve_item``
- ``reopen_item``
- ``close_item``
- ``item_summary``
- ``build_item_work_prompt``
- ``start_item_work``
- ``complete_item_stage``
- ``refine_item``
- ``item_memory_refs``
- ``resolve_item_memory``
- ``read_item_memory_body``
- ``write_item_memory_body``
- ``rename_item_memory``
- ``retag_item_memory``
- ``delete_item_memory``
- ``item_dossier``
- ``render_item_dossier_markdown``
- ``next_action_payload``

Memories (``taskledger.api.memories``):

- ``create_memory``
- ``list_memories``
- ``resolve_memory``
- ``read_memory_body``
- ``refresh_memory``
- ``rename_memory``
- ``write_memory_body``
- ``update_memory_body``
- ``update_memory_tags``
- ``delete_memory``

Repos (``taskledger.api.repos``):

- ``add_repo``
- ``list_repos``
- ``resolve_repo``
- ``resolve_repo_root``
- ``set_repo_role``
- ``set_default_execution_repo``
- ``clear_default_execution_repo``
- ``remove_repo``

Runs (``taskledger.api.runs``):

- ``list_runs``
- ``show_run``
- ``delete_run``
- ``cleanup_runs``
- ``promote_run_output``
- ``promote_run_report``
- ``apply_run_result``
- ``summarize_run_inventory``

Validation (``taskledger.api.validation``):

- ``list_validation_records``
- ``append_validation_record``
- ``remove_validation_records``
- ``summarize_validation_records``

Workflows (``taskledger.api.workflows``):

- ``list_workflows``
- ``resolve_workflow``
- ``save_workflow_definition``
- ``delete_workflow_definition``
- ``default_workflow_id``
- ``set_default_workflow``
- ``assign_item_workflow``
- ``item_workflow_state``
- ``item_stage_records``
- ``latest_stage_record``
- ``allowed_stage_transitions``
- ``can_enter_stage``
- ``enter_stage``
- ``mark_stage_running``
- ``mark_stage_succeeded``
- ``mark_stage_failed``
- ``mark_stage_needs_review``
- ``approve_stage``

Execution requests (``taskledger.api.execution_requests``):

- ``build_execution_request``
- ``expand_execution_request``
- ``record_execution_outcome``

Project config
^^^^^^^^^^^^^^

``taskledger.api.types.ProjectConfig`` carries the durable composition defaults
and additive workflow metadata used by ``taskledger next`` and
``taskledger report``:

- ``workflow_schema``
- ``project_context``
- ``artifact_rules``
- ``default_artifact_order``

Runs also expose ``summarize_run_inventory`` and ``apply_run_result`` through
``taskledger.api.runs`` for machine-readable inventory summaries and
item-aware run promotion.

Composite machine-facing helpers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The item, run, and context APIs now include higher-level helpers for thin
integrations that need one-shot machine payloads rather than low-level CRUD
orchestration:

- ``item_summary(...)`` returns compact item/workflow/memory/run/validation
  state.
- ``build_item_work_prompt(...)`` returns a workflow-aware prompt seed with
  target repo and save target hints.
- ``start_item_work(...)`` packages summary, prompt, and optional
  ``mark_running`` behavior into one call.
- ``complete_item_stage(...)`` wraps common stage-completion flow with optional
  run and validation attachments.
- ``refine_item(...)`` applies structured item refinements and returns the
  updated summary payload.
- ``apply_run_result(...)`` promotes run output or report content and can link
  it back to the related item and workflow stage.
- ``build_context_for_item(...)`` creates or refreshes an item-focused context
  entry and returns a machine-readable source summary.

Composition API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``taskledger.api.composition`` provides source expansion and bundle building:

.. code-block:: python

   from taskledger.api.composition import (
       SelectionRequest,
       expand_selection,
       build_sources,
       compose_bundle,
       describe_sources,
       repo_refs_for_sources,
       build_compose_payload,
   )

Minimal flow:

.. code-block:: python

   from taskledger.api.types import SourceBudget

   request = SelectionRequest(
       context_names=("my-context",),
       memory_refs=("mem-1",),
       directory_refs=("tests/",),
       file_render_mode="reference",
       include_item_memories=False,
   )
   expanded = expand_selection(workspace_root, request)
   sources = build_sources(
       workspace_root,
       expanded,
       default_context_order=("memory", "file", "item", "inline", "loop_artifact"),
       include_item_memories=request.include_item_memories,
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
           "directory_inputs": request.directory_refs,
           "item_inputs": request.item_refs,
           "inline_inputs": request.inline_texts,
           "loop_artifact_inputs": request.loop_latest_refs,
       },
       file_render_mode=request.file_render_mode,
       selected_repo_refs=repo_refs_for_sources(sources),
       run_in_repo=None,
       source_budget=SourceBudget(max_source_chars=12000, max_total_chars=48000),
       bundle=bundle,
   )

Runtime support API (Python only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``taskledger.api.runtime_support`` provides helpers for run artifact layout
and project configuration resolution:

.. code-block:: python

   from taskledger.api.runtime_support import (
       RunArtifactPaths,
       get_effective_project_config,
       create_run_artifact_layout,
       save_run_record,
       resolve_repo_root,
   )

Typical flow:

.. code-block:: python

   config = get_effective_project_config(workspace_root)
   layout = create_run_artifact_layout(workspace_root, origin="runtime")
   # runtime writes outputs into layout.run_dir
   save_run_record(workspace_root, run_record)
   repo_root = resolve_repo_root(workspace_root, "main-repo")

Workflow APIs
^^^^^^^^^^^^^

``taskledger.api.workflows`` provides the durable workflow model and stage
transition surface:

.. code-block:: python

   from taskledger.api.workflows import (
       assign_item_workflow,
       item_workflow_state,
       list_workflows,
       resolve_workflow,
       allowed_stage_transitions,
       enter_stage,
       mark_stage_succeeded,
   )

Execution-request APIs
^^^^^^^^^^^^^^^^^^^^^^

``taskledger.api.execution_requests`` builds and expands runner-facing workflow
contracts without launching a harness:

.. code-block:: python

   from taskledger.api.execution_requests import (
       build_execution_request,
       expand_execution_request,
       record_execution_outcome,
   )

Autogenerated reference
-----------------------

The sections below are generated from module docstrings.

Project API
-----------

.. automodule:: taskledger.api.project
   :members:
   :undoc-members:
   :show-inheritance:

Items API
---------

.. automodule:: taskledger.api.items
   :members:
   :undoc-members:
   :show-inheritance:

Memories API
------------

.. automodule:: taskledger.api.memories
   :members:
   :undoc-members:
   :show-inheritance:

Contexts API
------------

.. automodule:: taskledger.api.contexts
   :members:
   :undoc-members:
   :show-inheritance:

Repos API
---------

.. automodule:: taskledger.api.repos
   :members:
   :undoc-members:
   :show-inheritance:

Runs API
--------

.. automodule:: taskledger.api.runs
   :members:
   :undoc-members:
   :show-inheritance:

Validation API
--------------

.. automodule:: taskledger.api.validation
   :members:
   :undoc-members:
   :show-inheritance:

Composition API
---------------

.. automodule:: taskledger.api.composition
   :members:
   :undoc-members:
   :show-inheritance:

Runtime Support API
-------------------

.. automodule:: taskledger.api.runtime_support
   :members:
   :undoc-members:
   :show-inheritance:

Types API
---------

.. automodule:: taskledger.api.types
   :members:
   :undoc-members:
   :show-inheritance:

Search API
----------

.. automodule:: taskledger.api.search
   :members:
   :undoc-members:
   :show-inheritance:

Validation API
--------------

.. automodule:: taskledger.api.validation
   :members:
   :undoc-members:
   :show-inheritance:

CLI module
----------

.. automodule:: taskledger.cli
   :members:
   :undoc-members:
   :show-inheritance:
