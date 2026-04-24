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
   taskledger plan start rewrite-v2
   taskledger question add rewrite-v2 --text "Should exports include v2?"
   taskledger question answer rewrite-v2 q-0001 --text "Yes."
   taskledger plan propose rewrite-v2 --criterion "Accepted workflow is implemented." --file ./plan.md
   taskledger plan approve rewrite-v2 --version 1

   taskledger context rewrite-v2 --for implementation --format markdown
   taskledger implement start rewrite-v2
   taskledger implement log rewrite-v2 --message "Started implementation."
   taskledger implement change rewrite-v2 --path taskledger/storage/v2.py --kind edit --summary "Updated storage semantics."
   taskledger implement finish rewrite-v2 --summary "Implemented the approved plan."

   taskledger context rewrite-v2 --for validation --format markdown
   taskledger validate start rewrite-v2
   taskledger validate check rewrite-v2 --criterion ac-0001 --status pass --evidence "pytest -q tests/test_taskledger_v2_cli.py"
   taskledger validate finish rewrite-v2 --result passed --summary "Validated the rewrite."

Machine-readable output
-----------------------

.. code-block:: bash

   taskledger --json status --full
   taskledger --json task show rewrite-v2
   taskledger --json context rewrite-v2 --for validation --format json

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
       "healthy": true
     },
     "events": []
   }

Integrity and recovery
----------------------

.. code-block:: bash

   taskledger doctor
   taskledger doctor locks
   taskledger lock show rewrite-v2
   taskledger lock break rewrite-v2 --reason "recover stale planning lock"
   taskledger repair index

Export and snapshots
--------------------

.. code-block:: bash

   taskledger --json export
   taskledger import ./taskledger-export.json --replace
   taskledger snapshot ./artifacts
