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

Removed legacy surfaces
-----------------------

The old item/memory/repo/run/workflow/context/compose execution surfaces are not
part of the public compatibility contract. The corresponding CLI groups and
Python API modules have been removed rather than migrated.
