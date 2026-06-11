@area-monitor @feature-monitor @generated @needs-review
Feature: Monitor

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-monitor
  Rule: Monitor

    @bdd-monitor-monitor-snapshot-includes-active-task-and-progress @needs-review
    Example: Monitor Snapshot Includes Active Task And Progress
      Given the pytest test setup is prepared
      When monitor snapshot includes active task and progress is executed
      Then isinstance succeeds
      Then isinstance succeeds

    @bdd-monitor-monitor-snapshot-groups-in-progress-and-ready-tasks @needs-review
    Example: Monitor Snapshot Groups In Progress And Ready Tasks
      Given the pytest test setup is prepared
      When monitor snapshot groups in progress and ready tasks is executed
      Then planning.id is in in_progress_ids
      Then implementing.id is in in_progress_ids
      Then validating.id is in in_progress_ids
      Then ready is in ready_ids
      Then failed is in ready_ids

    @bdd-monitor-monitor-snapshot-lists-newest-activity-first @needs-review
    Example: Monitor Snapshot Lists Newest Activity First
      Given the pytest test setup is prepared
      When monitor snapshot lists newest activity first is executed
      Then isinstance succeeds
      Then activity is truthy

    @bdd-monitor-render-monitor-text-truncates-without-throwing @needs-review
    Example: Render Monitor Text Truncates Without Throwing
      Given the pytest test setup is prepared
      When render monitor text truncates without throwing is executed
      Then 'CURRENT WORK' is in rendered
      Then '...' is in rendered

    @bdd-monitor-monitor-cli-once-exits-zero @needs-review
    Example: Monitor Cli Once Exits Zero
      Given the pytest test setup is prepared
      When monitor cli once exits zero is executed
      Then result.exit_code equals 0
      Then 'CURRENT WORK' is in result.stdout

    @bdd-monitor-monitor-cli-json-once-emits-monitor-snapshot @needs-review
    Example: Monitor Cli Json Once Emits Monitor Snapshot
      Given the pytest test setup is prepared
      When monitor cli json once emits monitor snapshot is executed
      Then result.exit_code equals 0

    @bdd-monitor-empty-project-produces-snapshot
    Example: Empty initialized projects produce a monitor snapshot
      Given an initialized project has no tasks
      When a monitor snapshot is requested
      Then the snapshot is produced without error

    @bdd-monitor-plan-review-is-ready-work
    Example: Plan review tasks appear in ready work
      Given a task is awaiting plan review
      When a monitor snapshot is requested
      Then the task appears in the ready work group

    @bdd-monitor-task-activity-scope-filters-events
    Example: Task activity scope filters events to one task
      Given the ledger contains activity for multiple tasks
      When monitor activity is scoped to a selected task
      Then only activity for that task is returned

    @bdd-monitor-ledger-activity-scope-shows-all-events
    Example: Ledger activity scope shows activity across tasks
      Given the ledger contains activity for multiple tasks
      When monitor activity is scoped to the ledger
      Then activity across those tasks is returned

    @bdd-monitor-invalid-activity-scope-is-rejected
    Example: Invalid monitor activity scope is rejected
      Given an unsupported activity scope
      When the monitor command is invoked
      Then the command fails with a usage error
