Public surface
==============

``taskledger`` supports the task-first workflow:

.. code-block:: text

   task -> plan -> approval -> implement -> validate -> done

Supported CLI groups
--------------------

- ``task``, ``plan``, ``question``, ``implement``, ``validate``, ``todo``
- ``intro``, ``file``, ``link``, ``require``, ``lock``, ``handoff``
- ``doctor``, ``repair``, ``next-action``, ``can``, ``reindex``
- ``init``, ``status``, ``export``, ``import``, ``snapshot``
- ``context``, ``view``, ``serve``, ``search``, ``grep``, ``symbols``, ``deps``

``serve`` is a human-oriented, read-only localhost dashboard. Agents should
keep using the CLI and JSON command surface for automation.

The supported implementation lifecycle includes ``implement restart --summary
"..."`` when a task is in ``failed_validation``.

Small post-completion deltas use ``task follow-up PARENT_REF TITLE`` to create a
new child task instead of reopening a ``done`` task.

question subcommands
--------------------

- ``question add``, ``question list [--status STATUS]``, ``question answers [--format markdown|json]``
- ``question answer``, ``question answer-many``, ``question dismiss``, ``question open``, ``question status``

plan subcommands
----------------

- ``plan start``, ``plan propose``, ``plan upsert``, ``plan lint``, ``plan approve``, ``plan accept``, ``plan reject``, ``plan show``, ``plan diff``
- ``plan regenerate --from-answers``, ``plan materialize-todos``, ``plan command -- ...``

todo subcommands
----------------

- ``todo add``, ``todo list``, ``todo done``, ``todo show``, ``todo status``, ``todo next``
- Todo source is inferred from active lock: ``implementer`` during implementation, ``planner`` during planning, ``user`` otherwise.

Supported Python API modules
----------------------------

- ``taskledger.api.project``
- ``taskledger.api.tasks``
- ``taskledger.api.plans``
- ``taskledger.api.questions``
- ``taskledger.api.task_runs``
- ``taskledger.api.introductions``
- ``taskledger.api.locks``
- ``taskledger.api.handoff``
- ``taskledger.api.search``

``taskledger.api.task_runs`` includes the public lifecycle helpers
``start_implementation``, ``restart_implementation``, ``start_validation``, and
``finish_validation``.

Removed legacy surfaces
-----------------------

The old item/memory/repo/run/workflow/context/compose execution surfaces are not
part of the public compatibility contract. The corresponding CLI groups and
Python API modules have been removed rather than migrated.
