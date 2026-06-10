@area-agent_session_protocol @feature-agent-session-protocol @generated @needs-review
Feature: Agent Session Protocol

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-agent-session-protocol
  Rule: Agent Session Protocol

    @bdd-agent-session-protocol-lock-break-no-lock-message-mentions-next-action @needs-review
    Example: Lock Break No Lock Message Mentions Next Action
      Given the pytest test setup is prepared
      When lock break no lock message mentions next action is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-allow-empty-criteria-requires-reason @needs-review
    Example: Allow Empty Criteria Requires Reason
      Given the pytest test setup is prepared
      When allow empty criteria requires reason is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-allow-open-questions-requires-reason @needs-review
    Example: Allow Open Questions Requires Reason
      Given the pytest test setup is prepared
      When allow open questions requires reason is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-allow-empty-criteria-with-reason-succeeds @needs-review
    Example: Allow Empty Criteria With Reason Succeeds
      Given the pytest test setup is prepared
      When allow empty criteria with reason succeeds is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-plan-approval-blocks-when-no-todos @needs-review
    Example: Plan Approval Blocks When No Todos
      Given the pytest test setup is prepared
      When plan approval blocks when no todos is executed
      Then result.exit_code does not equal 0
      Then 'todo' is in message

    @bdd-agent-session-protocol-plan-approval-empty-todos-with-reason-succeeds @needs-review
    Example: Plan Approval Empty Todos With Reason Succeeds
      Given the pytest test setup is prepared
      When plan approval empty todos with reason succeeds is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-plan-approval-empty-todos-without-reason-fails @needs-review
    Example: Plan Approval Empty Todos Without Reason Fails
      Given the pytest test setup is prepared
      When plan approval empty todos without reason fails is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-plan-command-records-exit-code @needs-review
    Example: Plan Command Records Exit Code
      Given the pytest test setup is prepared
      When plan command records exit code is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-plan-command-fails-without-active-planning @needs-review
    Example: Plan Command Fails Without Active Planning
      Given the pytest test setup is prepared
      When plan command fails without active planning is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-plan-command-no-change-records @needs-review
    Example: Plan Command No Change Records
      Given the pytest test setup is prepared
      When plan command no change records is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-plan-command-mirrors-inner-exit-code-by-default @needs-review
    Example: Plan Command Mirrors Inner Exit Code By Default
      Given the pytest test setup is prepared
      When plan command mirrors inner exit code by default is executed
      Then result.exit_code equals 6

    @bdd-agent-session-protocol-plan-command-allow-failure-keeps-wrapper-exit-zero @needs-review
    Example: Plan Command Allow Failure Keeps Wrapper Exit Zero
      Given the pytest test setup is prepared
      When plan command allow failure keeps wrapper exit zero is executed
      Then raw.exit_code equals 0

    @bdd-agent-session-protocol-validate-finish-passed-blocks-unchecked-mandatory-criteria @needs-review
    Example: Validate Finish Passed Blocks Unchecked Mandatory Criteria
      Given the pytest test setup is prepared
      When validate finish passed blocks unchecked mandatory criteria is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-no-materialize-todos-without-reason-fails @needs-review
    Example: No Materialize Todos Without Reason Fails
      Given the pytest test setup is prepared
      When no materialize todos without reason fails is executed
      Then result.exit_code does not equal 0

    @bdd-agent-session-protocol-no-materialize-todos-with-reason-succeeds @needs-review
    Example: No Materialize Todos With Reason Succeeds
      Given the pytest test setup is prepared
      When no materialize todos with reason succeeds is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-todo-added-during-implementation-is-implementer-sourced @needs-review
    Example: Todo Added During Implementation Is Implementer Sourced
      Given the pytest test setup is prepared
      When todo added during implementation is implementer sourced is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-todo-added-during-planning-is-planner-sourced @needs-review
    Example: Todo Added During Planning Is Planner Sourced
      Given the pytest test setup is prepared
      When todo added during planning is planner sourced is executed
      Then result.exit_code equals 0

    @bdd-agent-session-protocol-todo-added-without-active-stage-defaults-to-user @needs-review
    Example: Todo Added Without Active Stage Defaults To User
      Given the pytest test setup is prepared
      When todo added without active stage defaults to user is executed
      Then result.exit_code equals 0
