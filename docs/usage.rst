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
   taskledger init --taskledger-dir /mnt/cloud/taskledger/project-a

``taskledger init`` writes ``taskledger.toml`` in the workspace root. The config
defaults to ``taskledger_dir = ".taskledger"``, but ``--taskledger-dir`` can
store durable taskledger state outside the source tree.

Task-first workflow
-------------------

.. code-block:: bash

   taskledger task create rewrite-v2 --description "Migrate to the task-first design."
   taskledger task activate rewrite-v2
   taskledger plan start
   taskledger question add --text "Should exports include v2?"
   taskledger question answer-many --text "q-0001: Yes."
   taskledger plan upsert --from-answers --criterion "Accepted workflow is implemented." --file ./plan.md
   taskledger plan lint --version 1
   taskledger plan accept --version 1 --note "Ready."

Fresh-context entrypoint
------------------------

Use ``taskledger next-action`` before a broad ``context`` read when you need the
next concrete work item instead of a generic stage summary.

.. code-block:: bash

   taskledger next-action
   taskledger --json next-action

Human output now names the next question, todo, criterion, or repair step and
includes the primary command hint. JSON output preserves the existing
``task_next_action`` fields and also includes ``next_item``, ``commands``, and
``progress``.

Agents should inspect ``next_item`` first, run ``next_command`` when it is safe,
avoid inventing question answers, and only mark todos done after evidence exists.

Compact implementation loop
---------------------------

For routine same-session implementation, prefer ``next-action`` and the next todo
over a broad generated context read:

.. code-block:: bash

   taskledger --json next-action
   taskledger --json todo next
   taskledger todo show todo-0003
   # implement only that todo
   pytest tests/...
   taskledger todo done todo-0003 --evidence "pytest tests/... passed"
   taskledger --json next-action

Rules for agents:

* Prefer ``next-action`` and ``todo next`` over generated context during normal work.
* Use the todo ``validation_hint`` before marking a todo done.
* Record concise evidence with ``todo done``.
* Do not create handoffs or context bundles unless the user asked to switch harness or session.

Human monitoring UI
-------------------

``taskledger serve`` starts a read-only localhost dashboard for a human
operator. It emphasizes the active task, next action, progress, blockers, and
compact task browsing while continuing to refresh with JSON polling and expose
no browser write actions.

.. code-block:: bash

   taskledger serve
   taskledger serve --open
   taskledger serve --task rewrite-v2 --refresh-ms 2000

Agents should continue to use ``next-action``, ``todo next``, and ``--json`` as
the canonical machine interface for routine same-session work. Reach for
``context`` or handoffs when the task actually needs broader fresh-context
transfer.

.. code-block:: text

   todo-work: Implementation is in progress; 1 todos remain.
   Next todo: todo-0001 -- Update next-action JSON payload.
   Command: taskledger todo show todo-0001
   Mark todo done after evidence exists: taskledger todo done todo-0001 --evidence "..."
   Progress: 0/1 todos done

.. code-block:: json

   {
     "kind": "task_next_action",
     "action": "todo-work",
     "next_command": "taskledger todo show todo-0001",
      "next_item": {
        "kind": "todo",
        "id": "todo-0001",
        "text": "Update next-action JSON payload.",
        "validation_hint": "Run: pytest tests/test_todo_implementation_gate.py -q; Expected: pass",
        "done_command_hint": "taskledger todo done todo-0001 --evidence \"...\""
      },
      "commands": [
        {
          "kind": "inspect",
          "label": "Show next todo",
          "command": "taskledger todo show todo-0001",
          "primary": true
        },
        {
          "kind": "complete",
          "label": "Mark todo done after evidence exists",
          "command": "taskledger todo done todo-0001 --evidence \"...\"",
          "primary": false
        }
      ],
     "progress": {
       "todos": {
         "total": 1,
         "done": 0,
         "open": 1,
         "open_ids": ["todo-0001"]
       }
     },
     "blocking": []
   }

All approval escape hatches require ``--reason``:

.. code-block:: bash

   taskledger plan approve --version 1 --actor user --note "Ready." --no-materialize-todos --reason "trivial task"
   taskledger plan approve --version 1 --actor user --note "Ready." --allow-empty-criteria --reason "no criteria needed"
   taskledger plan approve --version 1 --actor user --note "Ready." --allow-lint-errors --reason "user accepted rough plan"

Use ``plan command`` to record diagnostic commands during planning:

.. code-block:: bash

   taskledger plan command -- pytest tests/ -q

   taskledger context --for implementation --format markdown
   taskledger implement start
   taskledger implement log --message "Started implementation."
   taskledger implement change --path taskledger/storage/task_store.py --kind edit --summary "Updated storage semantics."
   taskledger implement finish --summary "Implemented the approved plan."

   taskledger context --for validation --format markdown
   taskledger validate start
   taskledger validate check --criterion ac-0001 --status pass --evidence "pytest -q tests/test_taskledger_v2_cli.py"
   taskledger validate finish --result passed --summary "Validated the rewrite."

If validation finds an implementation bug and the accepted plan is still
correct, restart implementation instead of replanning:

.. code-block:: bash

   taskledger validate finish --result failed --summary "Parser edge case still fails."
   taskledger next-action
   taskledger context --for implementation --format markdown
   taskledger implement restart --summary "Fix failed validation findings."

If validation finds an implementation bug and the accepted plan is still
correct, restart implementation instead of replanning:

.. code-block:: bash

   taskledger validate finish --result failed --summary "Parser edge case still fails."
   taskledger next-action
   taskledger context --for implementation --format markdown
   taskledger implement restart --summary "Fix failed validation findings."

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
        "workspace_root": "/workspace",
        "config_path": "/workspace/taskledger.toml",
        "taskledger_dir": "/workspace/.taskledger",
        "project_dir": "/workspace/.taskledger",
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

Cloud-backed storage
--------------------

Use one storage root per source project:

.. code-block:: bash

   taskledger init --taskledger-dir /mnt/cloud/taskledger/project-a

Do not point two unrelated repositories at the same ``taskledger_dir``.

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
