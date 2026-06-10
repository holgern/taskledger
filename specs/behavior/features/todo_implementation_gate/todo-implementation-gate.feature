@area-todo_implementation_gate @feature-todo-implementation-gate @generated @needs-review
Feature: Todo Implementation Gate

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-todo-implementation-gate
  Rule: Todo Implementation Gate

    @bdd-todo-implementation-gate-finish-blocked-by-open-todo @needs-review
    Example: Finish Blocked By Open Todo
      Given the pytest test setup is prepared
      When finish blocked by open todo is executed
      Then result.exit_code equals 0
      Then result.exit_code does not equal 0

    @bdd-todo-implementation-gate-finish-succeeds-when-todos-done @needs-review
    Example: Finish Succeeds When Todos Done
      Given the pytest test setup is prepared
      When finish succeeds when todos done is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-finish-succeeds-with-no-todos @needs-review
    Example: Finish Succeeds With No Todos
      Given the pytest test setup is prepared
      When finish succeeds with no todos is executed
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-finish-blocked-by-multiple-open-todos @needs-review
    Example: Finish Blocked By Multiple Open Todos
      Given the pytest test setup is prepared
      When finish blocked by multiple open todos is executed
      Then result.exit_code equals 0
      Then result.exit_code does not equal 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-finish-succeeds-after-all-todos-done @needs-review
    Example: Finish Succeeds After All Todos Done
      Given the pytest test setup is prepared
      When finish succeeds after all todos done is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-validation-status-open-todo-hint-uses-existing-command @needs-review
    Example: Validation Status Open Todo Hint Uses Existing Command
      Given the pytest test setup is prepared
      When validation status open todo hint uses existing command is executed
      Then result.exit_code equals 0
      Then hints is truthy
      Then all succeeds
      Then all succeeds

    @bdd-todo-implementation-gate-lock-remains-active-on-finish-failure @needs-review
    Example: Lock Remains Active On Finish Failure
      Given the pytest test setup is prepared
      When lock remains active on finish failure is executed
      Then result.exit_code equals 0
      Then result.exit_code does not equal 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-run-remains-running-on-finish-failure @needs-review
    Example: Run Remains Running On Finish Failure
      Given the pytest test setup is prepared
      When run remains running on finish failure is executed
      Then result.exit_code equals 0
      Then result.exit_code does not equal 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-error-payload-includes-blockers @needs-review
    Example: Error Payload Includes Blockers
      Given the pytest test setup is prepared
      When error payload includes blockers is executed
      Then result.exit_code does not equal 0
      Then 'open_todos' is in error_data
      Then 'blockers' is in error_data

    @bdd-todo-implementation-gate-four-todo-adds-all-visible-in-status @needs-review
    Example: Four Todo Adds All Visible In Status
      Given the pytest test setup is prepared
      When four todo adds all visible in status is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then listed_ids equals todo_ids
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-todo-next-json-includes-command-hints @needs-review
    Example: Todo Next Json Includes Command Hints
      Given the pytest test setup is prepared
      When todo next json includes command hints is executed
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-todo-next-human-output-shows-validation-hint-and-done-command @needs-review
    Example: Todo Next Human Output Shows Validation Hint And Done Command
      Given the pytest test setup is prepared
      When todo next human output shows validation hint and done command is executed
      Then result.exit_code equals 0
      Then 'Next todo: todo-0001' is in result.stdout
      Then 'Validation hint:' is in result.stdout
      Then _PLANNED_TODO_VALIDATION_HINT is in result.stdout
      Then 'Done command:' is in result.stdout
      Then 'taskledger todo done todo-0001 --evidence "..."' is in result.stdout

    @bdd-todo-implementation-gate-todo-show-human-output-shows-validation-hint-and-done-command @needs-review
    Example: Todo Show Human Output Shows Validation Hint And Done Command
      Given the pytest test setup is prepared
      When todo show human output shows validation hint and done command is executed
      Then result.exit_code equals 0
      Then 'todo-0001  open' is in result.stdout
      Then 'Update `taskledger/services/navigation.py` to expose compact todo hints.' is in result.stdout
      Then 'Validation hint:' is in result.stdout
      Then 'Done command:' is in result.stdout
      Then 'taskledger todo done todo-0001 --evidence "..."' is in result.stdout

    @bdd-todo-implementation-gate-next-action-includes-next-todo-payload-during-implementation @needs-review
    Example: Next Action Includes Next Todo Payload During Implementation
      Given the pytest test setup is prepared
      When next action includes next todo payload during implementation is executed
      Then result.exit_code equals 0
      Then any succeeds
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-next-action-includes-validation-hint-when-available @needs-review
    Example: Next Action Includes Validation Hint When Available
      Given the pytest test setup is prepared
      When next action includes validation hint when available is executed
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-next-action-human-output-names-next-todo @needs-review
    Example: Next Action Human Output Names Next Todo
      Given the pytest test setup is prepared
      When next action human output names next todo is executed
      Then result.exit_code equals 0
      Then 'todo-work: Implementation is in progress; 1 todos remain.' is in result.stdout
      Then 'Next todo: todo-0001' is in result.stdout
      Then 'Command: taskledger todo show todo-0001' is in result.stdout
      Then 'taskledger todo done todo-0001 --evidence "..."' is in result.stdout
      Then 'Progress: 0/1 todos done' is in result.stdout

    @bdd-todo-implementation-gate-next-action-returns-implement-finish-when-todos-are-done @needs-review
    Example: Next Action Returns Implement Finish When Todos Are Done
      Given the pytest test setup is prepared
      When next action returns implement finish when todos are done is executed
      Then added.exit_code equals 0
      Then done.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-next-action-orphaned-implementation-recommends-resume @needs-review
    Example: Next Action Orphaned Implementation Recommends Resume
      Given the pytest test setup is prepared
      When next action orphaned implementation recommends resume is executed
      Then broken.exit_code equals 0
      Then result.exit_code equals 0
      Then any succeeds
      Then any succeeds

    @bdd-todo-implementation-gate-next-action-does-not-call-orphaned-implementation-cancelled @needs-review
    Example: Next Action Does Not Call Orphaned Implementation Cancelled
      Given the pytest test setup is prepared
      When next action does not call orphaned implementation cancelled is executed
      Then broken.exit_code equals 0
      Then result.exit_code equals 0
      Then 'The task is cancelled.' is not in result.stdout
      Then 'implement-resume: Implementation run is running but the lock is missing.' is in result.stdout
      Then 'Next task: task-0001' is in result.stdout
      Then 'Command: taskledger implement resume --task task-0001 --reason "Reacquire implementation lock for existing running run."' is in result.stdout
      Then 'Blocker: Missing active implementation lock for run run-0002.' is in result.stdout

    @bdd-todo-implementation-gate-legacy-todos-yaml-is-ignored-in-normal-reads @needs-review
    Example: Legacy Todos Yaml Is Ignored In Normal Reads
      Given the pytest test setup is prepared
      When legacy todos yaml is ignored in normal reads is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-todo-implementation-gate-legacy-todos-yaml-does-not-block-finish @needs-review
    Example: Legacy Todos Yaml Does Not Block Finish
      Given the pytest test setup is prepared
      When legacy todos yaml does not block finish is executed
      Then result.exit_code equals 0
