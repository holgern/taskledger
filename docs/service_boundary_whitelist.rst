Service boundary whitelist
==========================

This note tracks temporary static-boundary whitelist entries enforced by
``tests/test_service_boundaries.py``.

The whitelist is debt tracking, not a permanent exception list. When an item
drops below budget or is removed, update this note and the related test
constants.

Module line budget whitelist (>2000 lines)
-----------------------------------------

* ``taskledger/services/tasks.py``

  * Current reason: Compatibility facade still contains multiple workflows in
    one file.
  * Target split direction: Split into ``task_lifecycle.py``,
    ``planning_flow.py``, ``implementation_flow.py``, ``validation_flow.py``,
    ``task_queries.py``, ``task_repair.py``, and ``command_capture.py``.

Current split status
--------------------

Implemented in this tranche:

* ``taskledger/services/planning_flow.py``
* ``taskledger/services/implementation_flow.py``
* ``taskledger/services/validation_flow.py``
* ``taskledger/services/tasks.py`` delegates plan, implement, and validate
  entrypoints to the new modules.

Remaining target: continue reducing ``taskledger/services/tasks.py`` to a
smaller compatibility facade and move residual helpers into focused modules.

Function line budget whitelist (>250 lines)
-------------------------------------------

* ``taskledger/cli_task.py::register_task_v2_commands``
* ``taskledger/cli_plan.py::register_plan_v2_commands``
* ``taskledger/cli_implement.py::register_implement_v2_commands``
* ``taskledger/services/doctor.py::inspect_v2_project``
* ``taskledger/services/navigation.py::can_perform``
* ``taskledger/services/web_dashboard.py::_render_dashboard_css``
* ``taskledger/services/web_dashboard.py::_render_dashboard_script``

Catch-all exception whitelist (``except Exception``)
----------------------------------------------------

Current allowed sites are listed with reasons in
``tests/test_service_boundaries.py`` under ``EXCEPT_EXCEPTION_WHITELIST``.

Policy intent:

* Allow catch-all handling only in doctor/repair and resilience wrappers.
* Block new catch-all sites unless explicitly reviewed and justified.
* Require whitelist edits to be intentional and reasoned.
