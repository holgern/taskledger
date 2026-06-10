@area-task_events @feature-task-events @generated @needs-review
Feature: Task Events

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-task-events
  Rule: Task Events

    @bdd-task-events-task-events-human-output @needs-review
    Example: Task Events Human Output
      Given the pytest test setup is prepared
      When task events human output is executed
      Then result.exit_code equals 0
      Then 'EVENTS' is in result.output
      Then 'task.created' is in result.output

    @bdd-task-events-task-events-json-output @needs-review
    Example: Task Events Json Output
      Given the pytest test setup is prepared
      When task events json output is executed
      Then isinstance succeeds
      Then 'event' is in event
      Then 'ts' is in event
      Then 'actor' is in event

    @bdd-task-events-task-events-all @needs-review
    Example: Task Events All
      Given the pytest test setup is prepared
      When task events all is executed
      Then result.exit_code equals 0
      Then 'task.created' is in result.output

    @bdd-task-events-task-events-limit @needs-review
    Example: Task Events Limit
      Given the pytest test setup is prepared
      When task events limit is executed
      Then result.exit_code equals 0

    @bdd-task-events-task-events-empty @needs-review
    Example: Task Events Empty
      Given the pytest test setup is prepared
      When task events empty is executed
      Then result.exit_code does not equal 0

    @bdd-task-events-task-events-with-explicit-task-ref @needs-review
    Example: Task Events With Explicit Task Ref
      Given the pytest test setup is prepared
      When task events with explicit task ref is executed
      Then result.exit_code equals 0
      Then 'EVENTS' is in result.output
