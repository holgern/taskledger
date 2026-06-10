@area-events @feature-events @generated @needs-review
Feature: Events

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-events
  Rule: Events

    @bdd-events-load-events-sorts-by-timestamp-and-event-id @needs-review
    Example: Load Events Sorts By Timestamp And Event Id
      Given the event log contains events written out of chronological order
      When the events are loaded
      Then they are returned sorted by timestamp and event id

    @bdd-events-load-events-rejects-duplicate-event-ids @needs-review
    Example: Load Events Rejects Duplicate Event Ids
      Given the event log contains duplicate event ids
      When the events are loaded
      Then loading fails with a duplicate event id error

    @bdd-events-load-recent-events-returns-chronological-task-tail @needs-review
    Example: Load Recent Events Returns Chronological Task Tail
      Given the event log contains events for multiple tasks
      When recent events are loaded for one task with a limit
      Then the returned events are that task's chronological tail
