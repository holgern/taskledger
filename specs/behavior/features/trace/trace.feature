@area-trace @feature-trace @generated @needs-review
Feature: Trace

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-trace
  Rule: Trace

    @bdd-trace-trace-cli-format-json-is-raw-json @needs-review
    Example: Trace Cli Format Json Is Raw Json
      Given the pytest test setup is prepared
      When trace cli format json is raw json is executed
      Then result.exit_code equals 0
