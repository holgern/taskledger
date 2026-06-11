@area-bdd_report_import @feature-bdd-report-import @generated @needs-review
Feature: Bdd Report Import

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-bdd-report-import
  Rule: Bdd Report Import

    @bdd-bdd-report-import-import-passing-junit-report @needs-review
    Example: Import Passing Junit Report
      Given the pytest test setup is prepared
      When import passing junit report is executed
      Then 'pytest_file: tests/test_task_management_plan_gates.py' is in evidence
      Then 'feature_file: specs/behavior/features/task-management/plan-gates.feature' is in evidence

    @bdd-bdd-report-import-cucumber-results-preserve-pass-and-fail
    Example: Cucumber results preserve pass and fail outcomes
      Given a Cucumber JSON report contains scenario results
      When Taskledger imports the behavior report
      Then passed scenarios remain passed
      And failed or non-passed scenarios do not become passing evidence

    @bdd-bdd-report-import-unmatched-failures-are-visible
    Example: Unmatched failing scenarios remain visible
      Given a behavior report contains a failing scenario without a known example
      When Taskledger imports the report
      Then the unmatched scenario is reported
      And its failing outcome is surfaced

    @bdd-bdd-report-import-invalid-input-is-rejected
    Example: Invalid report input is rejected
      Given the report file is missing, malformed, or uses an unsupported format
      When Taskledger imports the report
      Then import fails with a clear input error

    @bdd-bdd-report-import-junit-failure-remains-failed
    Example: Failing JUnit evidence remains failed
      Given a JUnit report contains a failing mapped test
      When Taskledger imports the behavior report
      Then the mapped behavior evidence is recorded as failed
