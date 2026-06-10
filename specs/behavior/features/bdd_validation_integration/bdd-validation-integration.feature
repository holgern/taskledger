@area-bdd_validation_integration @feature-bdd-validation-integration @generated @needs-review
Feature: Bdd Validation Integration

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-bdd-validation-integration
  Rule: Bdd Validation Integration

    @bdd-bdd-validation-integration-import-bdd-report-creates-validation-checks @needs-review
    Example: Import Bdd Report Creates Validation Checks
      Given the pytest test setup is prepared
      When import bdd report creates validation checks is executed
      Then result.exit_code equals 0
      Then validation_run.run_type equals 'validation'
      Then bdd_check.id equals 'check-0001'
      Then bdd_check.criterion_id equals 'ac-0001'
      Then bdd_check.status equals 'pass'
      Then 'scenario: @bdd-implementation-blocked-before-plan-acceptance' is in evidence_blob
      Then 'command: pytest tests/test_task_management_plan_gates.py' is in evidence_blob
      Then 'pytest_file: tests/test_task_management_plan_gates.py' is in evidence_blob
      Then 'report:' is in evidence_blob

    @bdd-bdd-validation-integration-failing-bdd-report-blocks-validation-finish @needs-review
    Example: Failing Bdd Report Blocks Validation Finish
      Given the pytest test setup is prepared
      When failing bdd report blocks validation finish is executed
      Then import_result.exit_code equals 0
      Then finish_result.exit_code does not equal 0

    @bdd-bdd-validation-integration-import-bdd-report-without-active-validation-fails-clearly @needs-review
    Example: Import Bdd Report Without Active Validation Fails Clearly
      Given the pytest test setup is prepared
      When import bdd report without active validation fails clearly is executed
      Then result.exit_code does not equal 0

    @bdd-bdd-validation-integration-import-bdd-report-without-accepted-plan-fails-clearly @needs-review
    Example: Import Bdd Report Without Accepted Plan Fails Clearly
      Given the pytest test setup is prepared
      When import bdd report without accepted plan fails clearly is executed
      Then result.exit_code does not equal 0
