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
   taskledger item show item-0001
   taskledger item approve item-0001
   taskledger item close item-0001

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

   taskledger context save parser-context --memory mem-0001 --item item-0001
   taskledger context list
   taskledger context show parser-context
   taskledger context rename parser-context --new-name release-parser-context
   taskledger context delete release-parser-context

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
   taskledger runs show 2026-04-21T09-00-00Z-abc123
   taskledger runs promote-output 2026-04-21T09-00-00Z-abc123 --name "Implementation notes"
   taskledger runs promote-report 2026-04-21T09-00-00Z-abc123 --name "Validation report"
   taskledger runs summary
   taskledger runs cleanup --keep 20
   taskledger runs delete 2026-04-21T09-00-00Z-abc123

Validation records
------------------

Validation records track durable evidence for work-item verification.

.. code-block:: bash

   taskledger validation add --item item-0001 --memory mem-0005 --kind smoke --status passed --verdict ok
   taskledger validation list
   taskledger validation summary
   taskledger validation remove --id val-0001

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
   taskledger workflow show default-item-v1
   taskledger workflow state item-0001
   taskledger workflow transitions item-0001

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
