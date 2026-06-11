@area-ready_work @feature-ready-work
Feature: Ready work

  Ready-work discovery exposes actionable tasks with explicit next commands.

  @rule-ready-work-selection
  Rule: Ready work selection

    @bdd-ready-work-filters-to-actionable-statuses
    Example: Ready work includes only actionable task statuses
      Given a ledger contains tasks in ready and non-ready lifecycle stages
      When ready work is listed
      Then only tasks in supported ready stages are returned

    @bdd-ready-work-includes-next-action-and-command
    Example: Ready work includes its next action and command
      Given a task is ready for lifecycle progress
      When ready work is listed
      Then the task includes its next action
      And the task includes an explicit command to perform that action

    @bdd-ready-work-respects-result-limit
    Example: Ready work respects the requested result limit
      Given more actionable tasks exist than the requested maximum
      When ready work is listed with that maximum
      Then no more than the requested number of tasks is returned
