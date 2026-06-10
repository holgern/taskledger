@area-help_subprocess @feature-help-subprocess @generated @needs-review
Feature: Help Subprocess

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-help-subprocess
  Rule: Help Subprocess

    @bdd-help-subprocess-help-subprocess-exits-quickly @needs-review
    Example: Help Subprocess Exits Quickly
      Given the pytest test setup is prepared
      When help subprocess exits quickly is executed
      Then result.returncode equals 0
      Then 'Usage:' is in result.stdout

    @bdd-help-subprocess-root-help-shows-completion-options @needs-review
    Example: Root Help Shows Completion Options
      Given the pytest test setup is prepared
      When root help shows completion options is executed
      Then result.returncode equals 0
      Then completion.returncode equals 0

    @bdd-help-subprocess-show-completion-exits-quickly-and-does-not-create-agent-logs @needs-review
    Example: Show Completion Exits Quickly And Does Not Create Agent Logs
      Given the pytest test setup is prepared
      When show completion exits quickly and does not create agent logs is executed
      Then result.returncode equals 0
      Then 'taskledger' is in result.stdout
