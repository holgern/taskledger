Usage
=====

Installation
------------

Install the package in editable mode during development:

.. code-block:: bash

   python -m pip install -e .
   python -m pip install -e ".[dev]"

Initialize project state
------------------------

Create the ``.taskledger/`` state directory in the current workspace:

.. code-block:: bash

   taskledger init

Work items
----------

Create, inspect, and move work items through the built-in lifecycle:

.. code-block:: bash

   taskledger item create parser-fix --text "Repair parser handling."
   taskledger item list
   taskledger item show parser-fix
   taskledger item view parser-fix
   taskledger item memory write parser-fix --role plan --text "1. Reproduce parser issue"
   taskledger item update parser-fix --add-label parser --add-acceptance "Parser tests pass"
   taskledger item approve parser-fix
   taskledger item close parser-fix

``taskledger item approve`` now requires planning evidence: non-empty plan memory
content, acceptance criteria, or validation checklist entries.

Composite item actions
^^^^^^^^^^^^^^^^^^^^^^

For machine-oriented integrations, use the composite item commands to reduce
multi-call orchestration:

.. code-block:: bash

   taskledger --json item summary parser-fix
   taskledger --json item work-prompt parser-fix
   taskledger --json item start parser-fix --mark-running
   taskledger --json item complete-stage parser-fix --stage implement --run run-1 --summary "Implemented parser tests"
   taskledger --json item refine parser-fix --description "Tighten parser fallback behavior" --acceptance "Parser tests pass"

``taskledger item summary`` returns a compact machine-facing payload with item
identity, workflow stage, next action, memory excerpts, recent runs, and recent
validation records. ``taskledger item work-prompt`` and ``taskledger item
start`` build on the same workflow state to provide a ready-to-use prompt seed
and execution metadata.

Memories
--------

Memories hold durable textual state such as analysis notes, plans, and
validation output.

.. code-block:: bash

   taskledger memory create "Failing tests" --text "pytest output"
   taskledger memory prepend failing-tests --text "Latest run:"
   taskledger memory retag failing-tests --add-tag analysis --add-tag parser
   taskledger memory rename failing-tests --new-name parser-analysis
   taskledger memory show parser-analysis
   taskledger memory delete parser-analysis

Contexts
--------

Contexts group saved references to memories, files, items, inline text, and
loop-artifact refs.

.. code-block:: bash

   taskledger context save parser-context --memory failing-tests --item parser-fix --dir tests/
   taskledger context list
   taskledger context show ctx-1
   taskledger context rename parser-context --new-name release-parser-context
   taskledger context delete release-parser-context
   taskledger --json context build-for-item parser-fix --save-as parser-fix-working

``taskledger context build-for-item`` creates or refreshes an item-focused
working context by gathering the item itself, linked memories, inline work
prompt material, and optional run/validation summaries into one saved context
entry.

Repositories and search
-----------------------

Register repositories so taskledger can search them and resolve the default
execution repo.

.. code-block:: bash

   taskledger repo add core --path /path/to/repo --role both
   taskledger repo set-role core --role write
   taskledger repo set-default core
   taskledger repo list
   taskledger search "parse error"
   taskledger grep "def create_"
   taskledger symbols "ProjectWorkItem"
   taskledger deps core package.module
   taskledger repo clear-default
   taskledger repo remove core

Runs
----

Saved run records can be inspected, promoted to memories, or cleaned up.

.. code-block:: bash

   taskledger runs list
   taskledger runs show run-1
   taskledger runs promote-output run-1 --name "Implementation notes"
   taskledger runs promote-report run-1 --name "Validation report"
   taskledger runs summary
   taskledger runs cleanup --keep 20
   taskledger runs delete run-1
   taskledger --json runs apply run-1 --as output --mark-stage-succeeded --summary "Implemented parser tests"
   taskledger --json run apply run-1 --as report

``taskledger runs apply`` (also available as ``taskledger run apply``) promotes
run output or report content into a memory, links it back onto the related item
when possible, and can optionally mark the related workflow stage succeeded.

Validation records
------------------

Validation records track durable evidence for work-item verification.

.. code-block:: bash

   taskledger memory create "Validation notes" --text "Smoke checks passed"
   taskledger validation add --item parser-fix --memory validation-notes --kind smoke --status passed --verdict ok
   taskledger validation list
   taskledger validation summary
   taskledger validation remove --id val-1

Project-level commands
----------------------

Use the top-level commands to inspect overall state:

.. code-block:: bash

   taskledger status
   taskledger board
   taskledger next
   taskledger doctor
   taskledger report

JSON output
-----------

Use ``--json`` for machine-readable output.

Composite item summary:

.. code-block:: bash

   taskledger --json item summary parser-fix

Status:

.. code-block:: bash

   taskledger --json status

.. code-block:: json

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

Item summary excerpt:

.. code-block:: json

   {
     "item": {
       "id": "it-1",
       "slug": "parser-fix",
       "status": "in_progress",
       "workflow_id": "default-item-v1",
       "stage": "implement",
       "target_repo_ref": "core"
     },
     "next_action": {
       "kind": "work_stage",
       "stage": "implement",
       "label": "Start implement"
     },
     "memories": {
       "analysis": {
         "ref": "mem-1",
         "excerpt": "Parser fallback still fails on nested input."
       }
     }
   }

Report:

.. code-block:: bash

   taskledger --json report

Export, import, and snapshots
-----------------------------

Export the current project state, import a saved payload, or materialize a
snapshot directory:

.. code-block:: bash

   taskledger --json export --include-bodies --include-run-artifacts
   taskledger import ./project-export.json --replace
   taskledger snapshot --output-dir ./artifacts --include-bodies

Example export payload excerpt:

.. code-block:: json

   {
     "kind": "project_export",
     "schema_version": 1,
     "counts": {
       "contexts": 1,
       "memories": 6,
       "repos": 1,
       "runs": 2,
       "validation_records": 1,
       "work_items": 1
     }
   }

Example import result:

.. code-block:: json

   {
     "kind": "project_import",
     "replace": true
   }

Example snapshot result:

.. code-block:: json

   {
     "kind": "project_snapshot",
     "snapshot_dir": "/tmp/project-snapshot-2026-04-21T09-00-00Z",
     "export_path": "/tmp/project-snapshot-2026-04-21T09-00-00Z/project-export.json"
   }

Workflow metadata
-----------------

``taskledger`` can use additive workflow metadata in ``.taskledger/project.toml``
to make ``taskledger next`` and ``taskledger report`` dependency-aware.

It also exposes first-class workflow inspection and transition commands:

.. code-block:: bash

   taskledger workflow list
   taskledger workflow save --from-file ./workflow.json
   taskledger workflow default
   taskledger workflow set-default custom-item-v1
   taskledger workflow delete custom-item-v1
   taskledger workflow show default-item-v1
   taskledger workflow records parser-fix
   taskledger workflow latest parser-fix plan
   taskledger workflow state parser-fix
   taskledger workflow can-enter parser-fix plan
   taskledger workflow transitions parser-fix
   taskledger workflow enter parser-fix plan
   taskledger workflow mark-running parser-fix plan --request-id req-1
   taskledger workflow mark-succeeded parser-fix plan --run-id run-1 --summary "Plan complete"
   taskledger workflow mark-needs-review parser-fix implement --reason "Manual review required"
   taskledger workflow mark-failed parser-fix implement --summary "Needs follow-up"
   taskledger workflow approve-stage parser-fix implement

Option B split contract:

- ``execution_requests``, ``composition``, and ``runtime_support`` are stable APIs.
- They are exposed through ``taskledger exec-request``, ``taskledger compose``, and
  ``taskledger runtime-support`` for CLI debugging flows.

Execution-request and composition CLI examples:

.. code-block:: bash

   taskledger --json exec-request build parser-fix plan --inline "Context"
   taskledger --json exec-request build parser-fix plan --file-mode reference --dir tests/ --file tests/test_file.py
   taskledger --json exec-request expand --request-file ./request.json
   taskledger --json exec-request record-outcome --request-file ./request.json --ok --text "Plan complete"
   taskledger --json compose expand --item parser-fix --inline "extra context"
   taskledger --json compose bundle --prompt "Plan this work" --item parser-fix
   taskledger --json compose bundle --prompt "Plan this work" --file-mode reference --dir tests/ --file tests/test_file.py
   taskledger --json compose bundle --prompt "Plan this work" --item parser-fix --no-item-memories
   taskledger --json runtime-support config
   taskledger --json runtime-support run-layout --origin debug
   taskledger --json runtime-support resolve-repo core

.. code-block:: toml

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

Loop-artifact references are stored durably on saved contexts via
``loop_latest_refs``. ``taskledger doctor`` reports missing loop-artifact paths
as broken context references instead of guessing runtime-owned locations.

Testing
-------

Run the pytest suite from the repository root:

.. code-block:: bash

   pytest -q

Documentation build
-------------------

Build the Sphinx docs locally:

.. code-block:: bash

   python -m pip install sphinx sphinx-rtd-theme
   sphinx-build -b html docs docs/_build/html
