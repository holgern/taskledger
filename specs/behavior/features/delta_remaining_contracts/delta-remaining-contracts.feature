@area-delta_remaining_contracts @feature-delta-remaining-contracts @generated @needs-review
Feature: Delta Remaining Contracts

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-delta-remaining-contracts
  Rule: Delta Remaining Contracts

    @bdd-delta-remaining-contracts-validation-pass-requires-mandatory-criteria-checks @needs-review
    Example: Validation Pass Requires Mandatory Criteria Checks
      Given the pytest test setup is prepared
      When validation pass requires mandatory criteria checks is executed
      Then result.exit_code equals 7

    @bdd-delta-remaining-contracts-validation-pass-accepts-canonical-criterion-check @needs-review
    Example: Validation Pass Accepts Canonical Criterion Check
      Given the pytest test setup is prepared
      When validation pass accepts canonical criterion check is executed
      Then result.exit_code equals 0

    @bdd-delta-remaining-contracts-context-dossier-and-link-alias-are-canonical @needs-review
    Example: Context Dossier And Link Alias Are Canonical
      Given the pytest test setup is prepared
      When context dossier and link alias are canonical is executed
      Then context.exit_code equals 0
      Then 'Planning Context' is in context.stdout
      Then '@README.md' is in context.stdout
      Then dossier.exit_code equals 0
      Then 'Task Dossier' is in dossier.stdout

    @bdd-delta-remaining-contracts-user-dependency-waiver-unblocks-implementation @needs-review
    Example: User Dependency Waiver Unblocks Implementation
      Given the pytest test setup is prepared
      When user dependency waiver unblocks implementation is executed
      Then blocked.exit_code equals 3
      Then allowed.exit_code equals 0

    @bdd-delta-remaining-contracts-import-smoke-tests @needs-review
    Example: Import Smoke Tests
      Given the pytest test setup is prepared
      When import smoke tests is executed
      Then Decision is not None
      Then PolicyDecision is not None
      Then PolicyDecision is Decision
      Then decision.ok is True
      Then decision.reason equals 'Test message'

    @bdd-delta-remaining-contracts-taskledger-main-import @needs-review
    Example: Taskledger Main Import
      Given the pytest test setup is prepared
      When taskledger main import is executed
      Then taskledger is not None

    @bdd-delta-remaining-contracts-reject-unknown-criterion-at-check-time @needs-review
    Example: Reject Unknown Criterion At Check Time
      Given the pytest test setup is prepared
      When reject unknown criterion at check time is executed
      Then result.exit_code does not equal 0

    @bdd-delta-remaining-contracts-latest-check-wins-semantics @needs-review
    Example: Latest Check Wins Semantics
      Given the pytest test setup is prepared
      When latest check wins semantics is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-delta-remaining-contracts-waiver-satisfies-criterion @needs-review
    Example: Waiver Satisfies Criterion
      Given the pytest test setup is prepared
      When waiver satisfies criterion is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-delta-remaining-contracts-validation-status-command-shows-blockers @needs-review
    Example: Validation Status Command Shows Blockers
      Given the pytest test setup is prepared
      When validation status command shows blockers is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-delta-remaining-contracts-mandatory-todo-blocks-validation-completion @needs-review
    Example: Mandatory Todo Blocks Validation Completion
      Given the pytest test setup is prepared
      When mandatory todo blocks validation completion is executed
      Then result.exit_code equals 7

    @bdd-delta-remaining-contracts-next-action-validation-includes-next-missing-criterion @needs-review
    Example: Next Action Validation Includes Next Missing Criterion
      Given the pytest test setup is prepared
      When next action validation includes next missing criterion is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-delta-remaining-contracts-next-action-validation-with-no-blockers-returns-finish @needs-review
    Example: Next Action Validation With No Blockers Returns Finish
      Given the pytest test setup is prepared
      When next action validation with no blockers returns finish is executed
      Then checked.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-delta-remaining-contracts-next-action-with-expired-lock-returns-repair-hint @needs-review
    Example: Next Action With Expired Lock Returns Repair Hint
      Given the pytest test setup is prepared
      When next action with expired lock returns repair hint is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-delta-remaining-contracts-task-follow-up-creates-linked-child-and-copies-lightweight-links @needs-review
    Example: Task Follow Up Creates Linked Child And Copies Lightweight Links
      Given the pytest test setup is prepared
      When task follow up creates linked child and copies lightweight links is executed
      Then result.exit_code equals 0

    @bdd-delta-remaining-contracts-task-follow-up-activate-sets-child-active-and-next-command @needs-review
    Example: Task Follow Up Activate Sets Child Active And Next Command
      Given the pytest test setup is prepared
      When task follow up activate sets child active and next command is executed
      Then result.exit_code equals 0

    @bdd-delta-remaining-contracts-task-follow-up-rejects-non-done-parent-without-mutating-state @needs-review
    Example: Task Follow Up Rejects Non Done Parent Without Mutating State
      Given the pytest test setup is prepared
      When task follow up rejects non done parent without mutating state is executed
      Then result.exit_code does not equal 0

    @bdd-delta-remaining-contracts-task-close-persists-closure-metadata-and-is-idempotent @needs-review
    Example: Task Close Persists Closure Metadata And Is Idempotent
      Given the pytest test setup is prepared
      When task close persists closure metadata and is idempotent is executed
      Then first.exit_code equals 0
      Then second.exit_code equals 0

    @bdd-delta-remaining-contracts-follow-up-relationships-render-in-show-dossier-and-context @needs-review
    Example: Follow Up Relationships Render In Show Dossier And Context
      Given the pytest test setup is prepared
      When follow up relationships render in show dossier and context is executed
      Then child_show.exit_code equals 0
      Then 'follow-up of: task-0001 Parent task' is in child_show.stdout
      Then parent_show.exit_code equals 0
      Then 'follow-ups: task-0002 Rename label' is in parent_show.stdout
      Then dossier.exit_code equals 0
      Then '## Follow-up Tasks' is in dossier.stdout
      Then 'task-0002 Rename label — draft' is in dossier.stdout
      Then context.exit_code equals 0
      Then '## Parent Task' is in context.stdout
      Then '- ID: task-0001' is in context.stdout
      Then '- Accepted plan: plan-v1' is in context.stdout
      Then '- Latest validation: run-0003 passed' is in context.stdout

    @bdd-delta-remaining-contracts-done-parent-next-action-stays-none-after-follow-up-creation @needs-review
    Example: Done Parent Next Action Stays None After Follow Up Creation
      Given the pytest test setup is prepared
      When done parent next action stays none after follow up creation is executed
      Then result.exit_code equals 0
