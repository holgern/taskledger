@area-tasks_service_static @feature-tasks-service-static @generated @needs-review
Feature: Tasks Service Static

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-tasks-service-static
  Rule: Tasks Service Static

    @bdd-tasks-service-static-services-tasks-has-no-duplicate-top-level-function-names @needs-review
    Example: Services Tasks Has No Duplicate Top Level Function Names
      Given the task service module source is parsed
      When top level function definitions are inspected
      Then no duplicate function names are present
