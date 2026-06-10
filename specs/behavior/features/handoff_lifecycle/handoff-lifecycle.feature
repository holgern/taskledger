@area-handoff_lifecycle @feature-handoff-lifecycle @generated @needs-review
Feature: Handoff Lifecycle

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-handoff-lifecycle
  Rule: Handoff Lifecycle

    @bdd-handoff-lifecycle-handoff-claim @needs-review
    Example: Handoff Claim
      Given the pytest test setup is prepared
      When handoff claim is executed
      Then claimed.status equals 'claimed'
      Then claimed.claimed_by is not None
      Then claimed.claimed_at is not None

    @bdd-handoff-lifecycle-handoff-close @needs-review
    Example: Handoff Close
      Given the pytest test setup is prepared
      When handoff close is executed
      Then closed.status equals 'closed'

    @bdd-handoff-lifecycle-handoff-cancel @needs-review
    Example: Handoff Cancel
      Given the pytest test setup is prepared
      When handoff cancel is executed
      Then cancelled.status equals 'cancelled'

    @bdd-handoff-lifecycle-handoff-lifecycle-sequence @needs-review
    Example: Handoff Lifecycle Sequence
      Given the pytest test setup is prepared
      When handoff lifecycle sequence is executed
      Then claimed.status equals 'claimed'
      Then closed.status equals 'closed'

    @bdd-handoff-lifecycle-handoff-create-stores-generated-context-for-todo @needs-review
    Example: Handoff Create Stores Generated Context For Todo
      Given the pytest test setup is prepared
      When handoff create stores generated context for todo is executed
      Then '## Focused Todo' is in handoff.context_body
      Then 'todo-0001' is in handoff.context_body

    @bdd-handoff-lifecycle-handoff-lifecycle-preserves-context-metadata-on-claim-close-cancel @needs-review
    Example: Handoff Lifecycle Preserves Context Metadata On Claim Close Cancel
      Given the pytest test setup is prepared
      When handoff lifecycle preserves context metadata on claim close cancel is executed
      Then claimed.context_for equals 'implementer'
      Then claimed.scope equals 'todo'
      Then claimed.todo_id equals 'todo-0001'
      Then claimed.focus_run_id is None
      Then closed.context_for equals 'implementer'
      Then closed.scope equals 'todo'
      Then closed.todo_id equals 'todo-0001'
      Then closed.context_body equals claimed.context_body
      Then cancelled.context_for equals 'implementer'
      Then cancelled.scope equals 'todo'
      Then cancelled.todo_id equals 'todo-0001'
