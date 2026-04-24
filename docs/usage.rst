Usage
=====

Installation
------------

.. code-block:: bash

   python -m pip install -e .
   python -m pip install -e ".[dev]"

Initialize state
----------------

.. code-block:: bash

   taskledger init

Task-first workflow
-------------------

.. code-block:: bash

   taskledger task create rewrite-v2 --description "Migrate to the task-first design."
   taskledger task activate rewrite-v2
   taskledger plan start
   taskledger question add --text "Should exports include v2?"
   taskledger question answer q-0001 --text "Yes."
   taskledger plan propose --criterion "Accepted workflow is implemented." --file ./plan.md
   taskledger plan approve --version 1 --actor user --note "Ready."

   taskledger context --for implementation --format markdown
   taskledger implement start
   taskledger implement log --message "Started implementation."
   taskledger implement change --path taskledger/storage/v2.py --kind edit --summary "Updated storage semantics."
   taskledger implement finish --summary "Implemented the approved plan."

   taskledger context --for validation --format markdown
   taskledger validate start
   taskledger validate check --criterion ac-0001 --status pass --evidence "pytest -q tests/test_taskledger_v2_cli.py"
   taskledger validate finish --result passed --summary "Validated the rewrite."

Machine-readable output
-----------------------

.. code-block:: bash

   taskledger --json status --full
   taskledger --json task active
   taskledger --json task show
   taskledger --json context --for validation --format json

.. code-block:: json

   {
     "ok": true,
     "command": "status",
     "result": {
       "kind": "taskledger_status",
       "counts": {
         "tasks": 1,
         "introductions": 0,
         "plans": 1,
         "questions": 1,
         "runs": 2,
         "changes": 1,
         "locks": 0
       },
       "active_task": null,
       "healthy": true
     },
     "events": []
   }

Integrity and recovery
----------------------

.. code-block:: bash

   taskledger doctor
   taskledger doctor locks
   taskledger lock show
   taskledger lock break --reason "recover stale planning lock"
   taskledger repair index

Export and snapshots
--------------------

.. code-block:: bash

   taskledger --json export
   taskledger import ./taskledger-export.json --replace
   taskledger snapshot ./artifacts
