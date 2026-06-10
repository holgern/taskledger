@area-json_contracts @feature-json-contracts @generated @needs-review
Feature: Json Contracts

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-json-contracts
  Rule: Json Contracts

    @bdd-json-contracts-json-success-envelope-uses-ok-command-result-and-events @needs-review
    Example: Json Success Envelope Uses Ok Command Result And Events
      Given the pytest test setup is prepared
      When json success envelope uses ok command result and events is executed
      Then result.exit_code equals 0

    @bdd-json-contracts-json-failure-envelope-includes-structured-error @needs-review
    Example: Json Failure Envelope Includes Structured Error
      Given the pytest test setup is prepared
      When json failure envelope includes structured error is executed
      Then result.exit_code equals 3

    @bdd-json-contracts-context-missing-todo-focus-returns-json-error @needs-review
    Example: Context Missing Todo Focus Returns Json Error
      Given the pytest test setup is prepared
      When context missing todo focus returns json error is executed
      Then result.exit_code equals 1

    @bdd-json-contracts-status-json-reports-workspace-and-storage-paths @needs-review
    Example: Status Json Reports Workspace And Storage Paths
      Given the pytest test setup is prepared
      When status json reports workspace and storage paths is executed
      Then result.exit_code equals 0

    @bdd-json-contracts-worker-pipeline-json-contracts-cover-guided-surfaces @needs-review
    Example: Worker Pipeline Json Contracts Cover Guided Surfaces
      Given the pytest test setup is prepared
      When worker pipeline json contracts cover guided surfaces is executed
      Then show_result.exit_code equals 0
      Then next_result.exit_code equals 0
      Then context_result.exit_code equals 0
      Then handoff_result.exit_code equals 0
      Then action_result.exit_code equals 0

    @bdd-json-contracts-python-m-taskledger-uses-canonical-json-command-names @needs-review
    Example: Python M Taskledger Uses Canonical Json Command Names
      Given the pytest test setup is prepared
      When python m taskledger uses canonical json command names is executed
      Then result.returncode equals 0

    @bdd-json-contracts-workflow-positional-task-ref-returns-json-usage-error-envelope @needs-review
    Example: Workflow Positional Task Ref Returns Json Usage Error Envelope
      Given the pytest test setup is prepared
      When workflow positional task ref returns json usage error envelope is executed
      Then result.exit_code equals 2

    @bdd-json-contracts-python-m-taskledger-json-parse-error-envelope @needs-review
    Example: Python M Taskledger Json Parse Error Envelope
      Given the pytest test setup is prepared
      When python m taskledger json parse error envelope is executed
      Then result.returncode equals 2

    @bdd-json-contracts-plan-lint-usage-error-includes-waiver-hint @needs-review
    Example: Plan Lint Usage Error Includes Waiver Hint
      Given the pytest test setup is prepared
      When plan lint usage error includes waiver hint is executed
      Then result.returncode equals 2
      Then 'Lint has no waiver flags' is in remediation
      Then 'allow-lint-errors' is in remediation

    @bdd-json-contracts-doctor-usage-error-for-errors-argument-has-specific-hint @needs-review
    Example: Doctor Usage Error For Errors Argument Has Specific Hint
      Given the pytest test setup is prepared
      When doctor usage error for errors argument has specific hint is executed
      Then result.returncode equals 2
      Then 'doctor locks' is in remediation
      Then 'doctor schema' is in remediation
