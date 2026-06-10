@area-plan_revision_workflow @feature-plan-revision-workflow @generated @needs-review
Feature: Plan Revision Workflow

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-plan-revision-workflow
  Rule: Plan Revision Workflow

    @bdd-plan-revision-workflow-plan-upsert-rejects-taskledger-storage-file @needs-review
    Example: Plan Upsert Rejects Taskledger Storage File
      Given the pytest test setup is prepared
      When plan upsert rejects taskledger storage file is executed
      Then result.exit_code equals 2

    @bdd-plan-revision-workflow-plan-propose-and-regenerate-reject-taskledger-storage-file @needs-review
    Example: Plan Propose And Regenerate Reject Taskledger Storage File
      Given the pytest test setup is prepared
      When plan propose and regenerate reject taskledger storage file is executed
      Then propose.exit_code equals 2
      Then regenerate.exit_code equals 2

    @bdd-plan-revision-workflow-plan-export-round-trips-after-revision @needs-review
    Example: Plan Export Round Trips After Revision
      Given the pytest test setup is prepared
      When plan export round trips after revision is executed
      Then export_result.exit_code equals 0
      Then upsert_result.exit_code equals 0

    @bdd-plan-revision-workflow-plan-amend-drops-criteria-and-todos-and-records-event @needs-review
    Example: Plan Amend Drops Criteria And Todos And Records Event
      Given the pytest test setup is prepared
      When plan amend drops criteria and todos and records event is executed
      Then amend.exit_code equals 0
      Then event_files is truthy
      Then any succeeds

    @bdd-plan-revision-workflow-plan-amend-unknown-criterion-fails-without-mutation @needs-review
    Example: Plan Amend Unknown Criterion Fails Without Mutation
      Given the pytest test setup is prepared
      When plan amend unknown criterion fails without mutation is executed
      Then amend.exit_code equals 2
      Then task.latest_plan_version equals 1

    @bdd-plan-revision-workflow-plan-upsert-auto-revise-from-plan-review @needs-review
    Example: Plan Upsert Auto Revise From Plan Review
      Given the pytest test setup is prepared
      When plan upsert auto revise from plan review is executed
      Then upsert.exit_code equals 0

    @bdd-plan-revision-workflow-plan-upsert-without-active-planning-suggests-revision-workflow @needs-review
    Example: Plan Upsert Without Active Planning Suggests Revision Workflow
      Given the pytest test setup is prepared
      When plan upsert without active planning suggests revision workflow is executed
      Then upsert.exit_code equals 3

    @bdd-plan-revision-workflow-next-action-plan-review-mentions-revision-commands @needs-review
    Example: Next Action Plan Review Mentions Revision Commands
      Given the pytest test setup is prepared
      When next action plan review mentions revision commands is executed
      Then next_action.exit_code equals 0
      Then 'Command: taskledger plan review --version 1' is in next_action.stdout
      Then 'Accept plan after explicit user approval: taskledger plan accept --version 1 --note "User approved in harness."' is in next_action.stdout
      Then 'Revise proposed plan: taskledger plan revise' is in next_action.stdout
      Then 'Export editable plan: taskledger plan export --version 1 --file ./plan.md' is in next_action.stdout
