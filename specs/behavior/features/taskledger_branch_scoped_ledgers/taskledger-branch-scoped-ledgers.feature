@area-taskledger_branch_scoped_ledgers @feature-taskledger-branch-scoped-ledgers @generated @needs-review
Feature: Taskledger Branch Scoped Ledgers

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-taskledger-branch-scoped-ledgers
  Rule: Taskledger Branch Scoped Ledgers

    @bdd-taskledger-branch-scoped-ledgers-two-ledgers-can-each-have-task-0030-and-hide-active-task @needs-review
    Example: Two Ledgers Can Each Have Task 0030 And Hide Active Task
      Given the pytest test setup is prepared
      When two ledgers can each have task 0030 and hide active task is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then 'task-0030' is in result.stdout
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then 'task-0030' is in result.stdout
      Then result.exit_code does not equal 0
      Then 'Feature task' is not in result.stdout

    @bdd-taskledger-branch-scoped-ledgers-ledger-fork-switch-status-and-doctor @needs-review
    Example: Ledger Fork Switch Status And Doctor
      Given the pytest test setup is prepared
      When ledger fork switch status and doctor is executed
      Then result.exit_code equals 0
      Then 'Ledger ref: main' is in result.stdout
      Then result.exit_code equals 0
      Then 'forked ledger main -> feature-a' is in result.stdout
      Then result.exit_code equals 0
      Then 'feature-a (current)' is in result.stdout
      Then result.exit_code equals 0
      Then 'switched feature-a -> main' is in result.stdout
      Then result.exit_code equals 0
      Then 'Healthy: yes' is in result.stdout

    @bdd-taskledger-branch-scoped-ledgers-ledger-adopt-renumbers-on-collision @needs-review
    Example: Ledger Adopt Renumbers On Collision
      Given the pytest test setup is prepared
      When ledger adopt renumbers on collision is executed
      Then result.exit_code equals 0
      Then 'renumbered' is in result.stdout

    @bdd-taskledger-branch-scoped-ledgers-doctor-reports-legacy-unscoped-state @needs-review
    Example: Doctor Reports Legacy Unscoped State
      Given the pytest test setup is prepared
      When doctor reports legacy unscoped state is executed
      Then result.exit_code equals 0
      Then 'Legacy unscoped path exists' is in result.stdout

    @bdd-taskledger-branch-scoped-ledgers-release-json-includes-ledger-ref @needs-review
    Example: Release Json Includes Ledger Ref
      Given the pytest test setup is prepared
      When release json includes ledger ref is executed
      Then result.exit_code equals 0
      Then '"ledger_ref": "main"' is in result.stdout
