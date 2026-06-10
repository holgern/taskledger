@area-taskledger_cli_api_parity @feature-taskledger-cli-api-parity @generated @needs-review
Feature: Taskledger Cli Api Parity

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-taskledger-cli-api-parity
  Rule: Taskledger Cli Api Parity

    @bdd-taskledger-cli-api-parity-cli-command-tree-matches-task-first-contract @needs-review
    Example: Cli Command Tree Matches Task First Contract
      Given the pytest test setup is prepared
      When cli command tree matches task first contract is executed
      Then result.exit_code equals 0
      Then name is in result.stdout

    @bdd-taskledger-cli-api-parity-legacy-cli-groups-are-removed @needs-review
    Example: Legacy Cli Groups Are Removed
      Given the pytest test setup is prepared
      When legacy cli groups are removed is executed
      Then result.exit_code does not equal 0

    @bdd-taskledger-cli-api-parity-task-first-subcommands-are-registered @needs-review
    Example: Task First Subcommands Are Registered
      Given the pytest test setup is prepared
      When task first subcommands are registered is executed
      Then result.exit_code equals 0
      Then subcommand is in result.stdout

    @bdd-taskledger-cli-api-parity-file-and-link-help-describe-distinct-surfaces @needs-review
    Example: File And Link Help Describe Distinct Surfaces
      Given the pytest test setup is prepared
      When file and link help describe distinct surfaces is executed
      Then file_help.exit_code equals 0
      Then link_help.exit_code equals 0
      Then 'Manage task file links.' is in file_help.stdout
      Then 'Manage external and typed task links.' is in link_help.stdout
