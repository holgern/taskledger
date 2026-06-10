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
