CLI Command Contract
====================

Taskledger uses a task-first command grammar:

.. code-block:: text

   taskledger [--root PATH] [--json] <area> <verb> [RESOURCE_REF] [--task TASK_REF] [options]

Global Options
--------------

* ``--root PATH`` selects the workspace root.
* ``--json`` is root-level only and must appear before the command group.
* Command-local ``--json`` options are not part of the public contract.

``--cwd`` remains accepted as a compatibility root alias, but docs and examples
should prefer ``--root``.

Task Scoping
------------

Task-scoped commands default to the active task. Use ``--task TASK_REF`` only
when explicitly targeting another task.

.. code-block:: bash

   taskledger plan start
   taskledger plan start --task task-0001
   taskledger implement finish --task task-0001 --summary "Implemented."
   taskledger validate status --task task-0001

Optional positional task refs are not supported.

Positional Resource Refs
------------------------

Positional refs are reserved for the direct resource being changed or shown:

.. code-block:: bash

   taskledger task activate TASK_REF
   taskledger todo done TODO_ID --task TASK_REF --evidence "pytest -q"
   taskledger question answer QUESTION_ID --task TASK_REF --text "Yes."
   taskledger handoff show HANDOFF_ID --task TASK_REF
   taskledger require add REQUIRED_TASK_REF --task TASK_REF

Focused context and handoff options
-----------------------------------

Focused worker contexts keep lifecycle ``mode`` separate from worker-role
``--for``:

.. code-block:: bash

   taskledger context --for planner|implementer|validator|spec-reviewer|code-reviewer|reviewer|full [--scope task|todo|run] [--todo TODO_ID] [--run RUN_ID] [--format markdown|json|text] [--task TASK_REF]
   taskledger handoff create --mode planning|implementation|validation|review|full [--for planner|implementer|validator|spec-reviewer|code-reviewer|reviewer|full] [--scope task|todo|run] [--todo TODO_ID] [--run RUN_ID] [--task TASK_REF]
   taskledger handoff show HANDOFF_ID --format text|markdown|json [--task TASK_REF]

Rules:

* ``--todo`` implies ``--scope todo``.
* ``--run`` implies ``--scope run``.
* ``--scope todo`` requires ``--todo``.
* ``--scope run`` requires ``--run``.
* ``--for implementation|validation|planning|review|full`` remain accepted as
  compatibility aliases.
* ``handoff show --format markdown`` prints the stored snapshot body.

Removed Pre-Release Aliases
---------------------------

These aliases are intentionally not registered:

* ``task new``
* ``task clear-active``
* ``implement add-change``
* ``validate add-check``
* ``file link``
* ``file unlink``
* ``link link``
* ``link unlink``

Use ``task create``, ``task deactivate``, ``implement change``,
``validate check``, ``file add``, ``file remove``, ``link add``, and
``link remove`` instead.
