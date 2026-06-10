@area-worker_pipeline_handoff @feature-worker-pipeline-handoff @generated @needs-review
Feature: Worker Pipeline Handoff

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-worker-pipeline-handoff
  Rule: Worker Pipeline Handoff

    @bdd-worker-pipeline-handoff-worker-handoff-stores-worker-step-id-sparse @needs-review
    Example: Worker Handoff Stores Worker Step Id Sparse
      Given the pytest test setup is prepared
      When worker handoff stores worker step id sparse is executed
      Then worker_result.exit_code equals 0
      Then normal_result.exit_code equals 0
      Then 'worker_step_id' is not in normal_payload

    @bdd-worker-pipeline-handoff-worker-handoff-rejects-conflicting-mode-override @needs-review
    Example: Worker Handoff Rejects Conflicting Mode Override
      Given the pytest test setup is prepared
      When worker handoff rejects conflicting mode override is executed
      Then result.exit_code does not equal 0
      Then "requires mode 'implementation'" is in output

    @bdd-worker-pipeline-handoff-worker-handoff-rejects-conflicting-context-override @needs-review
    Example: Worker Handoff Rejects Conflicting Context Override
      Given the pytest test setup is prepared
      When worker handoff rejects conflicting context override is executed
      Then result.exit_code does not equal 0
      Then "requires context 'implementer'" is in output
