@area-plan_todo_materialization @feature-plan-todo-materialization @generated @needs-review
Feature: Plan Todo Materialization

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-plan-todo-materialization
  Rule: Plan Todo Materialization

    @bdd-plan-todo-materialization-plan-approval-materializes-structured-todos-once @needs-review
    Example: Plan Approval Materializes Structured Todos Once
      Given a proposed plan contains structured todo front matter
      When the plan is approved
      Then the structured todos are materialized once for the task
