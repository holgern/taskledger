@area-worker_pipeline_config @feature-worker-pipeline-config @generated @needs-review
Feature: Worker Pipeline Config

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-worker-pipeline-config
  Rule: Worker Pipeline Config

    @bdd-worker-pipeline-config-no-worker-pipeline-section-preserves-default-config @needs-review
    Example: No Worker Pipeline Section Preserves Default Config
      Given the pytest test setup is prepared
      When no worker pipeline section preserves default config is executed
      Then config.worker_pipeline is None

    @bdd-worker-pipeline-config-disabled-worker-pipeline-section-returns-disabled-config @needs-review
    Example: Disabled Worker Pipeline Section Returns Disabled Config
      Given the pytest test setup is prepared
      When disabled worker pipeline section returns disabled config is executed
      Then config.worker_pipeline is not None

    @bdd-worker-pipeline-config-worker-pipeline-parse-three-step-config @needs-review
    Example: Worker Pipeline Parse Three Step Config
      Given the pytest test setup is prepared
      When worker pipeline parse three step config is executed
      Then config.worker_pipeline is not None
      Then config.worker_pipeline.enabled is True
      Then config.worker_pipeline.name equals 'simple-three-context'
      Then config.worker_pipeline.mode equals 'guided'

    @bdd-worker-pipeline-config-worker-pipeline-parse-four-step-config-without-skeletor @needs-review
    Example: Worker Pipeline Parse Four Step Config Without Skeletor
      Given the pytest test setup is prepared
      When worker pipeline parse four step config without skeletor is executed
      Then config.worker_pipeline is not None

    @bdd-worker-pipeline-config-worker-pipeline-parse-custom-worker-name @needs-review
    Example: Worker Pipeline Parse Custom Worker Name
      Given the pytest test setup is prepared
      When worker pipeline parse custom worker name is executed
      Then config.worker_pipeline is not None
      Then api_designer.label equals 'Api Designer'
      Then api_designer.todo_tag equals 'api-design'
      Then domain_reviewer.actor_role equals 'reviewer'

    @bdd-worker-pipeline-config-invalid-config-is-rejected
    Example: Invalid worker pipeline configuration is rejected
      Given an enabled pipeline has missing steps, duplicate IDs, or invalid fields
      When Taskledger validates project configuration
      Then configuration loading fails with a validation error
