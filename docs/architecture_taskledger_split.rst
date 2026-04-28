Taskledger architecture
=======================

``taskledger`` is a task-first CLI and Python package for staged coding work.
The canonical workflow is:

.. code-block:: text

   task -> plan -> approval -> implement -> validate -> done

Owning layers
-------------

* ``taskledger/domain/`` owns lifecycle enums, policies, and record models.
* ``taskledger/storage/v2.py`` and ``taskledger/storage/locks.py`` own persisted
  task bundles and visible lock files under ``.taskledger/``.
* ``taskledger/services/tasks.py`` owns task lifecycle orchestration.
* ``taskledger/services/handoff.py`` owns handoff payloads and rendering.
* ``taskledger/services/doctor_v2.py`` owns integrity checks.
* ``taskledger/api/*`` exposes public wrappers.
* ``taskledger/cli*.py`` wires commands only.

Storage model
-------------

Markdown records are canonical. Task, plan, and run reads come from those
records directly. JSON files under ``.taskledger/indexes/`` are optional derived
caches or registries. Active stages require visible lock files, and stale locks
are reported instead of being cleared silently.

Command surface
---------------

The supported command groups are ``task``, ``plan``, ``question``, ``implement``,
``validate``, ``todo``, ``intro``, ``file``, ``link``, ``require``, ``lock``,
``handoff``, ``context``, ``actor``, ``view``, ``next-action``, ``can``, ``search``,
``grep``, ``symbols``, ``deps``, ``doctor``, ``repair``, ``reindex``, ``init``,
``status``, ``export``, ``import``, and ``snapshot``.
