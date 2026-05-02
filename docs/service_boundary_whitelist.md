# Service boundary whitelist

This note tracks temporary static-boundary whitelist entries enforced by `tests/test_service_boundaries.py`.

The whitelist is debt tracking, not a permanent exception list. When an item drops below the budget or is removed, update both this note and the test constants.

## Module line budget whitelist (>2000 lines)

| Module                         | Current reason                                                      | Target split direction                                                                                                                                                                                                      |
| ------------------------------ | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `taskledger/services/tasks.py` | Compatibility facade still contains multiple workflows in one file. | Split into `task_lifecycle.py`, `planning.py`, `implementation.py`, `validation_flow.py`, `task_queries.py`, `task_repair.py`, `command_capture.py`. Keep `services/tasks.py` as transitional facade until imports migrate. |

## Function line budget whitelist (>250 lines)

| Function                                                         | Current reason                           | Target split direction                                                         |
| ---------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------ |
| `taskledger/cli_task.py::register_task_v2_commands`              | Large nested registration callback.      | Move to per-command callbacks or split into task submodules by command family. |
| `taskledger/cli_plan.py::register_plan_v2_commands`              | Large nested registration callback.      | Move to per-command callbacks or split into plan submodules.                   |
| `taskledger/cli_implement.py::register_implement_v2_commands`    | Large nested registration callback.      | Move to per-command callbacks or split into implementation submodules.         |
| `taskledger/services/doctor.py::inspect_v2_project`              | Many independent checks in one function. | Extract focused inspectors and aggregate report assembly.                      |
| `taskledger/services/navigation.py::can_perform`                 | Dense lifecycle decision logic.          | Move gate decisions into shared pure decision/snapshot layer.                  |
| `taskledger/services/web_dashboard.py::_render_dashboard_css`    | Embedded static CSS in Python.           | Move CSS to static resource under `taskledger/services/web/`.                  |
| `taskledger/services/web_dashboard.py::_render_dashboard_script` | Embedded static JS in Python.            | Move JS to static resource under `taskledger/services/web/`.                   |

## Catch-all exception whitelist (`except Exception`)

Current allowed sites are listed with reasons in `tests/test_service_boundaries.py` (`EXCEPT_EXCEPTION_WHITELIST`).

Policy intent:

- allow catch-all handling in doctor/repair and resilience wrappers only
- block new catch-all sites unless they are explicitly reviewed and justified
- require whitelist edits to be intentional and reasoned
