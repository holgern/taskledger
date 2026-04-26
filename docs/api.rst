API reference
=============

`taskledger` exposes a task-first public API through ``taskledger.api``.

Supported modules
-----------------

- ``taskledger.api.project``
- ``taskledger.api.tasks``
- ``taskledger.api.plans``
- ``taskledger.api.questions``
- ``taskledger.api.task_runs``
- ``taskledger.api.introductions``
- ``taskledger.api.locks``
- ``taskledger.api.handoff``
- ``taskledger.api.search``

Import boundary
---------------

Consumers should not import from ``taskledger.storage``, ``taskledger.services``,
``taskledger.domain``, or ``taskledger.search`` directly.

Project API
-----------

- ``init_project``
- ``project_status``
- ``project_status_summary``
- ``project_doctor``
- ``project_export``
- ``project_import``
- ``project_snapshot``

Task API
--------

- ``create_task``
- ``show_active_task``
- ``activate_task``
- ``deactivate_task``
- ``clear_active_task``
- ``resolve_active_task``
- ``list_task_summaries``
- ``show_task``
- ``edit_task``
- ``cancel_task``
- ``close_task``
- ``add_requirement``
- ``remove_requirement``
- ``waive_requirement``
- ``add_file_link``
- ``remove_file_link``
- ``list_file_links``
- ``add_todo``
- ``set_todo_done``
- ``show_todo``
- ``todo_status``
- ``next_todo``
- ``task_dossier``
- ``next_action``
- ``can_perform``
- ``reindex``
- ``repair_task_record``

Plan API
--------

- ``start_planning``
- ``propose_plan``
- ``list_plan_versions``
- ``show_plan``
- ``diff_plan``
- ``approve_plan``
- ``reject_plan``
- ``revise_plan``
- ``regenerate_plan_from_answers``
- ``materialize_plan_todos``
- ``run_planning_command``

Question API
------------

- ``add_question``
- ``list_questions``
- ``list_open_questions``
- ``answer_question``
- ``dismiss_question``
- ``question_status``

Run API
-------

- ``start_implementation``
- ``log_implementation``
- ``add_implementation_deviation``
- ``add_implementation_artifact``
- ``add_change``
- ``scan_changes``
- ``run_implementation_command``
- ``finish_implementation``
- ``show_task_run``
- ``start_validation``
- ``add_validation_check``
- ``validation_status``
- ``waive_criterion``
- ``finish_validation``
- ``list_runs``
- ``list_changes``

Other APIs
----------

- ``taskledger.api.introductions``: create/list/resolve/link introductions
- ``taskledger.api.locks``: inspect and break locks
- ``taskledger.api.handoff``: render handoff context
- ``taskledger.api.search``: workspace search, grep, symbols, and deps
