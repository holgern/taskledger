@area-worker_pipeline_cli @feature-worker-pipeline-cli @generated @needs-review
Feature: Worker Pipeline Cli

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-worker-pipeline-cli
  Rule: Worker Pipeline Cli

    @bdd-worker-pipeline-cli-pipeline-commands-print-no-config-message @needs-review
    Example: Pipeline Commands Print No Config Message
      Given the pytest test setup is prepared
      When pipeline commands print no config message is executed
      Then result.exit_code equals 0

    @bdd-worker-pipeline-cli-pipeline-commands-print-disabled-message @needs-review
    Example: Pipeline Commands Print Disabled Message
      Given the pytest test setup is prepared
      When pipeline commands print disabled message is executed
      Then result.exit_code equals 0

    @bdd-worker-pipeline-cli-pipeline-show-and-list-render-enabled-config @needs-review
    Example: Pipeline Show And List Render Enabled Config
      Given the pytest test setup is prepared
      When pipeline show and list render enabled config is executed
      Then show_result.exit_code equals 0
      Then list_result.exit_code equals 0
      Then 'planner' is in list_result.stdout
      Then 'Test Writer' is in list_result.stdout
      Then 'reviewer' is in list_result.stdout

    @bdd-worker-pipeline-cli-pipeline-next-returns-planner-before-plan-acceptance @needs-review
    Example: Pipeline Next Returns Planner Before Plan Acceptance
      Given the pytest test setup is prepared
      When pipeline next returns planner before plan acceptance is executed
      Then result.exit_code equals 0

    @bdd-worker-pipeline-cli-pipeline-next-advances-after-closed-worker-review-handoff @needs-review
    Example: Pipeline Next Advances After Closed Worker Review Handoff
      Given the pytest test setup is prepared
      When pipeline next advances after closed worker review handoff is executed
      Then first.exit_code equals 0
      Then second.exit_code equals 0

    @bdd-worker-pipeline-cli-pipeline-next-advances-after-passing-code-review-record @needs-review
    Example: Pipeline Next Advances After Passing Code Review Record
      Given the pytest test setup is prepared
      When pipeline next advances after passing code review record is executed
      Then before.exit_code equals 0
      Then record.exit_code equals 0
      Then after.exit_code equals 0

    @bdd-worker-pipeline-cli-pipeline-next-keeps-code-review-when-latest-review-failed @needs-review
    Example: Pipeline Next Keeps Code Review When Latest Review Failed
      Given the pytest test setup is prepared
      When pipeline next keeps code review when latest review failed is executed
      Then record.exit_code equals 0
      Then next_step.exit_code equals 0

    @bdd-worker-pipeline-cli-pipeline-next-ignores-cancelled-worker-review-handoff @needs-review
    Example: Pipeline Next Ignores Cancelled Worker Review Handoff
      Given the pytest test setup is prepared
      When pipeline next ignores cancelled worker review handoff is executed
      Then handoff.exit_code equals 0
      Then cancel.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-worker-pipeline-cli-next-action-guided-worker-pipeline-payload-and-commands @needs-review
    Example: Next Action Guided Worker Pipeline Payload And Commands
      Given the pytest test setup is prepared
      When next action guided worker pipeline payload and commands is executed
      Then result.exit_code equals 0

    @bdd-worker-pipeline-cli-next-action-guided-worker-pipeline-human-output @needs-review
    Example: Next Action Guided Worker Pipeline Human Output
      Given the pytest test setup is prepared
      When next action guided worker pipeline human output is executed
      Then result.exit_code equals 0
      Then 'Worker step: tester' is in result.stdout
      Then 'Worker context: taskledger pipeline context tester' is in result.stdout
      Then 'Worker handoff: taskledger handoff create --worker tester --summary "..."' is in result.stdout

    @bdd-worker-pipeline-cli-pipeline-next-ignores-normal-review-handoff @needs-review
    Example: Pipeline Next Ignores Normal Review Handoff
      Given the pytest test setup is prepared
      When pipeline next ignores normal review handoff is executed
      Then handoff.exit_code equals 0
      Then close.exit_code equals 0
      Then result.exit_code equals 0
