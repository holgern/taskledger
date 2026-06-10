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
