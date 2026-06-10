@area-plan_approval_contract @feature-plan-approval-contract @generated @needs-review
Feature: Plan Approval Contract

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-plan-approval-contract
  Rule: Plan Approval Contract

    @bdd-plan-approval-contract-plan-approval-records-actor-metadata-and-criteria-ids @needs-review
    Example: Plan Approval Records Actor Metadata And Criteria Ids
      Given the pytest test setup is prepared
      When plan approval records actor metadata and criteria ids is executed
      Then approve.exit_code equals 0
      Then isinstance succeeds

    @bdd-plan-approval-contract-plan-approval-warns-when-source-is-missing @needs-review
    Example: Plan Approval Warns When Source Is Missing
      Given the pytest test setup is prepared
      When plan approval warns when source is missing is executed
      Then approve.exit_code equals 0
      Then isinstance succeeds
      Then any succeeds

    @bdd-plan-approval-contract-task-report-warns-when-approved-plan-hash-mismatches @needs-review
    Example: Task Report Warns When Approved Plan Hash Mismatches
      Given the pytest test setup is prepared
      When task report warns when approved plan hash mismatches is executed
      Then approve.exit_code equals 0
      Then report.exit_code equals 0
      Then 'approved plan content hash does not match' is in report.stdout

    @bdd-plan-approval-contract-plan-approval-blocks-running-planning-run-without-lock @needs-review
    Example: Plan Approval Blocks Running Planning Run Without Lock
      Given the pytest test setup is prepared
      When plan approval blocks running planning run without lock is executed
      Then task.latest_planning_run is not None
      Then approve.exit_code does not equal 0

    @bdd-plan-approval-contract-plan-approval-rejects-agent-approval-without-escape-hatch @needs-review
    Example: Plan Approval Rejects Agent Approval Without Escape Hatch
      Given the pytest test setup is prepared
      When plan approval rejects agent approval without escape hatch is executed
      Then approve.exit_code does not equal 0

    @bdd-plan-approval-contract-plan-approval-requires-criteria-by-default @needs-review
    Example: Plan Approval Requires Criteria By Default
      Given the pytest test setup is prepared
      When plan approval requires criteria by default is executed
      Then approve.exit_code does not equal 0

    @bdd-plan-approval-contract-plan-accept-human-error-includes-lint-issue-details @needs-review
    Example: Plan Accept Human Error Includes Lint Issue Details
      Given the pytest test setup is prepared
      When plan accept human error includes lint issue details is executed
      Then result.exit_code does not equal 0
      Then 'Plan lint details:' is in combined
      Then 'missing_todos' is in combined
      Then 'plan.todos' is in combined

    @bdd-plan-approval-contract-plan-approve-default-actor-is-agent @needs-review
    Example: Plan Approve Default Actor Is Agent
      Given the pytest test setup is prepared
      When plan approve default actor is agent is executed
      Then approve.exit_code does not equal 0

    @bdd-plan-approval-contract-plan-yaml-single-key-shorthand-criteria @needs-review
    Example: Plan Yaml Single Key Shorthand Criteria
      Given the pytest test setup is prepared
      When plan yaml single key shorthand criteria is executed
      Then show.exit_code equals 0
