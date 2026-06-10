@area-services_dashboard @feature-services-dashboard @generated @needs-review
Feature: Services Dashboard

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-services-dashboard
  Rule: Services Dashboard

    @bdd-services-dashboard-dashboard-next-action @needs-review
    Example: Dashboard Next Action
      Given the pytest test setup is prepared
      When dashboard next action is executed
      Then isinstance succeeds
      Then 'action' is in na

    @bdd-services-dashboard-render-dashboard-text-basic @needs-review
    Example: Render Dashboard Text Basic
      Given the pytest test setup is prepared
      When render dashboard text basic is executed
      Then 'My Task' is in text
      Then 'implementing' is in text
      Then 'Plan: none' is in text
      Then 'Runs: none' is in text
      Then 'Changes: none' is in text
      Then 'Lock: none' is in text

    @bdd-services-dashboard-render-dashboard-text-with-plan @needs-review
    Example: Render Dashboard Text With Plan
      Given the pytest test setup is prepared
      When render dashboard text with plan is executed
      Then 'Plan (v2): approved' is in text
      Then 'ac-0001: All tests pass' is in text
      Then 'ac-0002: Coverage above 80%' is in text
      Then 'Questions: 1 open / 1 total' is in text
      Then 'Todos: 2/4 done' is in text
      Then '[x] todo-0001  Write tests' is in text
      Then '[x] todo-0002  Fix bug' is in text
      Then '[ ] todo-0003  Add docs' is in text
      Then '[ ] todo-0004  Clean up' is in text
      Then 'Files: 3 linked' is in text

    @bdd-services-dashboard-render-dashboard-text-with-next-action @needs-review
    Example: Render Dashboard Text With Next Action
      Given the pytest test setup is prepared
      When render dashboard text with next action is executed
      Then 'Next action: todo-work' is in text
      Then 'Implementation is in progress; 1 todos remain.' is in text
      Then 'next todo: todo-0001  Wire detailed next-action output.' is in text
      Then 'validation: pytest tests/test_services_dashboard.py -q' is in text
      Then 'when done: taskledger todo done todo-0001 --evidence "..."' is in text
      Then 'command: taskledger todo show todo-0001' is in text
      Then 'progress: 2/3 todos done' is in text
      Then 'blocker: Missing requirement X' is in text

    @bdd-services-dashboard-render-dashboard-text-with-runs @needs-review
    Example: Render Dashboard Text With Runs
      Given the pytest test setup is prepared
      When render dashboard text with runs is executed
      Then 'run-0001' is in text
      Then 'implementation' is in text
      Then 'completed' is in text
      Then 'Did some work' is in text
      Then '[passed]' is in text

    @bdd-services-dashboard-render-dashboard-text-with-changes @needs-review
    Example: Render Dashboard Text With Changes
      Given the pytest test setup is prepared
      When render dashboard text with changes is executed
      Then 'Changes: 1' is in text
      Then 'change-0001' is in text
      Then 'src/main.py' is in text
      Then 'Fixed bug' is in text

    @bdd-services-dashboard-render-dashboard-text-with-lock @needs-review
    Example: Render Dashboard Text With Lock
      Given the pytest test setup is prepared
      When render dashboard text with lock is executed
      Then 'Lock: implementing (run-0001)' is in text

    @bdd-services-dashboard-render-dashboard-text-with-metadata @needs-review
    Example: Render Dashboard Text With Metadata
      Given the pytest test setup is prepared
      When render dashboard text with metadata is executed
      Then 'Full Task' is in text
      Then 'Description: A summary of the task' is in text
      Then 'Priority: high' is in text
      Then 'Labels: bug, urgent' is in text
      Then 'Owner: alice' is in text
      Then 'implementing' is in text
