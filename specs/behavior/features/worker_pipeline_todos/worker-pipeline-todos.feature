@area-worker_pipeline_todos @feature-worker-pipeline-todos @generated @needs-review
Feature: Worker Pipeline Todos

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-worker-pipeline-todos
  Rule: Worker Pipeline Todos

    @bdd-worker-pipeline-todos-pipeline-next-returns-first-open-worker-todo @needs-review
    Example: Pipeline Next Returns First Open Worker Todo
      Given the pytest test setup is prepared
      When pipeline next returns first open worker todo is executed
      Then result.exit_code equals 0

    @bdd-worker-pipeline-todos-plan-todo-worker-step-requires-enabled-pipeline @needs-review
    Example: Plan Todo Worker Step Requires Enabled Pipeline
      Given the pytest test setup is prepared
      When plan todo worker step requires enabled pipeline is executed
      Then result.exit_code does not equal 0
      Then 'requires an enabled worker pipeline' is in output
