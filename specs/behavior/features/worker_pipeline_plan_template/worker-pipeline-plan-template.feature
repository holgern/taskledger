@area-worker_pipeline_plan_template @feature-worker-pipeline-plan-template @generated @needs-review
Feature: Worker Pipeline Plan Template

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-worker-pipeline-plan-template
  Rule: Worker Pipeline Plan Template

    @bdd-worker-pipeline-plan-template-plan-template-unchanged-without-worker-pipeline @needs-review
    Example: Plan Template Unchanged Without Worker Pipeline
      Given the pytest test setup is prepared
      When plan template unchanged without worker pipeline is executed
      Then result.exit_code equals 0
      Then '## Optional worker pipeline todo hints' is not in result.stdout
      Then 'worker_step:' is not in result.stdout

    @bdd-worker-pipeline-plan-template-plan-template-requires-opt-in-flag-for-worker-pipeline-hints @needs-review
    Example: Plan Template Requires Opt In Flag For Worker Pipeline Hints
      Given the pytest test setup is prepared
      When plan template requires opt in flag for worker pipeline hints is executed
      Then result.exit_code equals 0
      Then '## Optional worker pipeline todo hints' is not in result.stdout
      Then 'api-designer' is not in result.stdout

    @bdd-worker-pipeline-plan-template-worker-plan-template-uses-configured-steps-not-hardcoded-names @needs-review
    Example: Worker Plan Template Uses Configured Steps Not Hardcoded Names
      Given the pytest test setup is prepared
      When worker plan template uses configured steps not hardcoded names is executed
      Then result.exit_code equals 0
      Then '## Optional worker pipeline todo hints' is in result.stdout
      Then 'worker_step: "api-designer"' is in result.stdout
      Then 'worker_step: "coder"' is in result.stdout
      Then 'skeletor' is not in result.stdout

    @bdd-worker-pipeline-plan-template-plan-template-worker-hints-require-template-or-guided-mode @needs-review
    Example: Plan Template Worker Hints Require Template Or Guided Mode
      Given the pytest test setup is prepared
      When plan template worker hints require template or guided mode is executed
      Then result.exit_code does not equal 0
      Then "mode = 'template' or 'guided'" is in output
