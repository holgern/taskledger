@area-taskledger_v2_cli @feature-taskledger-v2-cli @generated @needs-review
Feature: Taskledger V2 Cli

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-taskledger-v2-cli
  Rule: Taskledger V2 Cli

    @bdd-taskledger-v2-cli-implement-command-mirrors-inner-exit-code-by-default @needs-review
    Example: Implement Command Mirrors Inner Exit Code By Default
      Given the pytest test setup is prepared
      When implement command mirrors inner exit code by default is executed
      Then result.exit_code equals 7

    @bdd-taskledger-v2-cli-implement-command-allow-failure-keeps-wrapper-exit-zero @needs-review
    Example: Implement Command Allow Failure Keeps Wrapper Exit Zero
      Given the pytest test setup is prepared
      When implement command allow failure keeps wrapper exit zero is executed
      Then raw.exit_code equals 0

    @bdd-taskledger-v2-cli-planning-guidance-is-recommended-then-not-repeated @needs-review
    Example: Planning Guidance Is Recommended Then Not Repeated
      Given the pytest test setup is prepared
      When planning guidance is recommended then not repeated is executed
      Then start.exit_code equals 0
      Then 'Next: taskledger plan guidance' is in start.stdout
      Then guidance.exit_code equals 0

    @bdd-taskledger-v2-cli-v2-task-lifecycle-and-handoff @needs-review
    Example: V2 Task Lifecycle And Handoff
      Given the pytest test setup is prepared
      When v2 task lifecycle and handoff is executed
      Then isinstance succeeds
      Then isinstance succeeds
      Then handoff_result.exit_code equals 0
      Then 'Code Changes' is in handoff_result.stdout
      Then 'taskledger/storage/task_store.py' is in handoff_result.stdout

    @bdd-taskledger-v2-cli-v2-lock-break-and-expired-lock-report @needs-review
    Example: V2 Lock Break And Expired Lock Report
      Given the pytest test setup is prepared
      When v2 lock break and expired lock report is executed
      Then doctor_result.exit_code equals 0
      Then 'task-0001' is in doctor_result.stdout
      Then break_result.exit_code equals 0

    @bdd-taskledger-v2-cli-doctor-human-reports-non-looping-implementation-mismatch-hint @needs-review
    Example: Doctor Human Reports Non Looping Implementation Mismatch Hint
      Given the pytest test setup is prepared
      When doctor human reports non looping implementation mismatch hint is executed
      Then result.exit_code equals 0
      Then 'Run/lock mismatches:' is in result.stdout
      Then 'taskledger implement resume' is in result.stdout
      Then 'taskledger doctor' is not in result.stdout

    @bdd-taskledger-v2-cli-doctor-verbose-option-is-supported @needs-review
    Example: Doctor Verbose Option Is Supported
      Given the pytest test setup is prepared
      When doctor verbose option is supported is executed
      Then result.exit_code equals 0
      Then 'healthy:' is in result.stdout

    @bdd-taskledger-v2-cli-implement-resume-does-not-create-new-run @needs-review
    Example: Implement Resume Does Not Create New Run
      Given the pytest test setup is prepared
      When implement resume does not create new run is executed
      Then result.exit_code equals 0

    @bdd-taskledger-v2-cli-implement-resume-requires-reason @needs-review
    Example: Implement Resume Requires Reason
      Given the pytest test setup is prepared
      When implement resume requires reason is executed
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires --reason.' is in result.stdout

    @bdd-taskledger-v2-cli-next-action-recommends-repair-for-orphaned-planning-run @needs-review
    Example: Next Action Recommends Repair For Orphaned Planning Run
      Given the pytest test setup is prepared
      When next action recommends repair for orphaned planning run is executed
      Then result.exit_code equals 0

    @bdd-taskledger-v2-cli-can-implement-blocker-names-orphaned-planning-run @needs-review
    Example: Can Implement Blocker Names Orphaned Planning Run
      Given the pytest test setup is prepared
      When can implement blocker names orphaned planning run is executed
      Then result.exit_code equals 0

    @bdd-taskledger-v2-cli-implement-start-reports-running-run-details @needs-review
    Example: Implement Start Reports Running Run Details
      Given the pytest test setup is prepared
      When implement start reports running run details is executed
      Then result.exit_code does not equal 0

    @bdd-taskledger-v2-cli-repair-run-finishes-orphaned-planning-run @needs-review
    Example: Repair Run Finishes Orphaned Planning Run
      Given the pytest test setup is prepared
      When repair run finishes orphaned planning run is executed
      Then result.exit_code equals 0

    @bdd-taskledger-v2-cli-implement-resume-rejects-missing-accepted-plan @needs-review
    Example: Implement Resume Rejects Missing Accepted Plan
      Given the pytest test setup is prepared
      When implement resume rejects missing accepted plan is executed
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires an accepted plan version.' is in result.stdout

    @bdd-taskledger-v2-cli-implement-resume-rejects-non-running-implementation-run @needs-review
    Example: Implement Resume Rejects Non Running Implementation Run
      Given the pytest test setup is prepared
      When implement resume rejects non running implementation run is executed
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires a running implementation run.' is in result.stdout

    @bdd-taskledger-v2-cli-implement-resume-rejects-non-implementation-run @needs-review
    Example: Implement Resume Rejects Non Implementation Run
      Given the pytest test setup is prepared
      When implement resume rejects non implementation run is executed
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires a running implementation run.' is in result.stdout

    @bdd-taskledger-v2-cli-implement-resume-rejects-existing-lock @needs-review
    Example: Implement Resume Rejects Existing Lock
      Given the pytest test setup is prepared
      When implement resume rejects existing lock is executed
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires no active lock.' is in result.stdout

    @bdd-taskledger-v2-cli-implement-resume-rejects-completed-task @needs-review
    Example: Implement Resume Rejects Completed Task
      Given the pytest test setup is prepared
      When implement resume rejects completed task is executed
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires approved or implementing state.' is in result.stdout

    @bdd-taskledger-v2-cli-implement-resume-rejects-cancelled-task @needs-review
    Example: Implement Resume Rejects Cancelled Task
      Given the pytest test setup is prepared
      When implement resume rejects cancelled task is executed
      Then cancel.exit_code equals 0
      Then result.exit_code does not equal 0
      Then 'Implementation resume requires approved or implementing state.' is in result.stdout

    @bdd-taskledger-v2-cli-task-uncancel-restores-cancelled-task-to-approved @needs-review
    Example: Task Uncancel Restores Cancelled Task To Approved
      Given the pytest test setup is prepared
      When task uncancel restores cancelled task to approved is executed
      Then cancel.exit_code equals 0

    @bdd-taskledger-v2-cli-next-action-after-uncancel-running-implementation-recommends-resume @needs-review
    Example: Next Action After Uncancel Running Implementation Recommends Resume
      Given the pytest test setup is prepared
      When next action after uncancel running implementation recommends resume is executed
      Then cancel.exit_code equals 0
      Then uncancel.exit_code equals 0
      Then any succeeds

    @bdd-taskledger-v2-cli-can-implement-blocks-existing-running-run-after-uncancel @needs-review
    Example: Can Implement Blocks Existing Running Run After Uncancel
      Given the pytest test setup is prepared
      When can implement blocks existing running run after uncancel is executed
      Then any succeeds

    @bdd-taskledger-v2-cli-uncancel-non-cancelled-orphan-hints-resume @needs-review
    Example: Uncancel Non Cancelled Orphan Hints Resume
      Given the pytest test setup is prepared
      When uncancel non cancelled orphan hints resume is executed
      Then result.exit_code does not equal 0
      Then any succeeds

    @bdd-taskledger-v2-cli-task-uncancel-rejects-active-stage-target @needs-review
    Example: Task Uncancel Rejects Active Stage Target
      Given the pytest test setup is prepared
      When task uncancel rejects active stage target is executed
      Then cancel.exit_code equals 0
      Then result.exit_code does not equal 0
      Then 'Invalid uncancel target: implementing' is in result.stdout

    @bdd-taskledger-v2-cli-repair-task-human-output-records-inspection-and-recovery-hint @needs-review
    Example: Repair Task Human Output Records Inspection And Recovery Hint
      Given the pytest test setup is prepared
      When repair task human output records inspection and recovery hint is executed
      Then cancel.exit_code equals 0
      Then result.exit_code equals 0
      Then 'recorded repair inspection for task-0001' is in result.stdout
      Then 'warning: Recorded a repair inspection event only; no task state was changed.' is in result.stdout
      Then 'recovery: taskledger task uncancel --reason "Restore the task to a safe durable stage."' is in result.stdout

    @bdd-taskledger-v2-cli-task-first-support-commands-are-available @needs-review
    Example: Task First Support Commands Are Available
      Given the pytest test setup is prepared
      When task first support commands are available is executed
      Then file_list.exit_code equals 0
      Then '@README.md [doc]' is in file_list.stdout

    @bdd-taskledger-v2-cli-root-alias-uses-stable-json-envelope @needs-review
    Example: Root Alias Uses Stable Json Envelope
      Given the pytest test setup is prepared
      When root alias uses stable json envelope is executed
      Then init_result.exit_code equals 0

    @bdd-taskledger-v2-cli-plan-approval-blocks-open-questions-with-json-error @needs-review
    Example: Plan Approval Blocks Open Questions With Json Error
      Given the pytest test setup is prepared
      When plan approval blocks open questions with json error is executed
      Then result.exit_code equals 3

    @bdd-taskledger-v2-cli-expired-lock-requires-explicit-break-json-error @needs-review
    Example: Expired Lock Requires Explicit Break Json Error
      Given the pytest test setup is prepared
      When expired lock requires explicit break json error is executed
      Then result.exit_code equals 4

    @bdd-taskledger-v2-cli-context-for-implementer-todo-renders-focused-context @needs-review
    Example: Context For Implementer Todo Renders Focused Context
      Given the pytest test setup is prepared
      When context for implementer todo renders focused context is executed
      Then result.exit_code equals 0
      Then 'Implementation Context' is in result.stdout
      Then '## Worker Role' is in result.stdout
      Then 'role: implementer' is in result.stdout
      Then 'scope: todo' is in result.stdout
      Then 'focused_todo: todo-0001' is in result.stdout
      Then '## Focused Todo' is in result.stdout
      Then 'todo-0001' is in result.stdout
      Then '[ ] todo-0001' is not in result.stdout

    @bdd-taskledger-v2-cli-context-for-spec-reviewer-run-renders-review-context @needs-review
    Example: Context For Spec Reviewer Run Renders Review Context
      Given the pytest test setup is prepared
      When context for spec reviewer run renders review context is executed
      Then result.exit_code equals 0
      Then 'Review Context' is in result.stdout
      Then 'role: spec-reviewer' is in result.stdout
      Then 'scope: run' is in result.stdout
      Then '## Spec Compliance Review' is in result.stdout
      Then 'acceptance_criteria_findings' is in result.stdout
      Then 'deviations_from_plan' is in result.stdout

    @bdd-taskledger-v2-cli-context-for-code-reviewer-run-renders-review-context @needs-review
    Example: Context For Code Reviewer Run Renders Review Context
      Given the pytest test setup is prepared
      When context for code reviewer run renders review context is executed
      Then result.exit_code equals 0
      Then 'Review Context' is in result.stdout
      Then 'role: code-reviewer' is in result.stdout
      Then 'scope: run' is in result.stdout
      Then '## Code Quality Review' is in result.stdout
      Then 'maintainability' is in result.stdout
      Then 'test_coverage_gaps' is in result.stdout

    @bdd-taskledger-v2-cli-handoff-create-and-show-focused-todo-snapshot @needs-review
    Example: Handoff Create And Show Focused Todo Snapshot
      Given the pytest test setup is prepared
      When handoff create and show focused todo snapshot is executed
      Then show_result.exit_code equals 0
      Then 'Implementation Context' is in show_result.stdout
      Then '## Worker Role' is in show_result.stdout
      Then '## Focused Todo' is in show_result.stdout
      Then 'todo-0001' is in show_result.stdout

    @bdd-taskledger-v2-cli-repair-planning-command-changes-dry-run @needs-review
    Example: Repair Planning Command Changes Dry Run
      Given the pytest test setup is prepared
      When repair planning command changes dry run is executed
      Then create_result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-taskledger-v2-cli-repair-planning-command-changes-requires-reason @needs-review
    Example: Repair Planning Command Changes Requires Reason
      Given the pytest test setup is prepared
      When repair planning command changes requires reason is executed
      Then create_result.exit_code equals 0
      Then result.exit_code does not equal 0

    @bdd-taskledger-v2-cli-status-command-with-check-flag @needs-review
    Example: Status Command With Check Flag
      Given the pytest test setup is prepared
      When status command with check flag is executed
      Then result.exit_code equals 0
      Then isinstance succeeds

    @bdd-taskledger-v2-cli-status-command-without-check-flag-fast @needs-review
    Example: Status Command Without Check Flag Fast
      Given the pytest test setup is prepared
      When status command without check flag fast is executed
      Then result.exit_code equals 0
      Then isinstance succeeds

    @bdd-taskledger-v2-cli-lock-show-human-reports-dead-holder-pid-and-next-commands @needs-review
    Example: Lock Show Human Reports Dead Holder Pid And Next Commands
      Given the pytest test setup is prepared
      When lock show human reports dead holder pid and next commands is executed
      Then result.exit_code equals 0
      Then 'LOCK task-0001' is in result.stdout
      Then 'classification: active_dead_local_process' is in result.stdout
      Then 'pid=999999' is in result.stdout
      Then 'taskledger repair lock --task task-0001 --reason "Holder PID 999999 is no longer running."' is in result.stdout
      Then 'taskledger implement resume --task task-0001 --reason "Reacquire implementation lock after stale holder repair."' is in result.stdout
      Then 'storage:' is in result.stdout
      Then 'lock file:' is in result.stdout

    @bdd-taskledger-v2-cli-lock-show-json-payload-includes-diagnostics-and-storage-fields @needs-review
    Example: Lock Show Json Payload Includes Diagnostics And Storage Fields
      Given the pytest test setup is prepared
      When lock show json payload includes diagnostics and storage fields is executed
      Then result.exit_code equals 0
      Then 'storage_root' is in result_data
      Then 'inside_workspace' is in result_data
      Then isinstance succeeds

    @bdd-taskledger-v2-cli-implement-resume-with-active-dead-pid-lock-explains-repair-not-expired-resume @needs-review
    Example: Implement Resume With Active Dead Pid Lock Explains Repair Not Expired Resume
      Given the pytest test setup is prepared
      When implement resume with active dead pid lock explains repair not expired resume is executed
      Then result.exit_code does not equal 0
      Then 'non-expired' is in message
      Then '--repair-expired-lock only applies after the lock expires' is in message
      Then any succeeds
      Then any succeeds

    @bdd-taskledger-v2-cli-next-action-dead-pid-lock-routes-to-repair-lock @needs-review
    Example: Next Action Dead Pid Lock Routes To Repair Lock
      Given the pytest test setup is prepared
      When next action dead pid lock routes to repair lock is executed
      Then result.exit_code equals 0
      Then lock_blockers is truthy

    @bdd-taskledger-v2-cli-next-action-live-lock-keeps-todo-work-with-warning @needs-review
    Example: Next Action Live Lock Keeps Todo Work With Warning
      Given the pytest test setup is prepared
      When next action live lock keeps todo work with warning is executed
      Then result.exit_code equals 0
      Then 'lock_status' is in next_action
