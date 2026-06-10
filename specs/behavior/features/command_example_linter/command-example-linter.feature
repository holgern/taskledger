@area-command_example_linter @feature-command-example-linter @generated @needs-review
Feature: Command Example Linter

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-command-example-linter
  Rule: Command Example Linter

    @bdd-command-example-linter-docs-do-not-reference-removed-commands @needs-review
    Example: Docs Do Not Reference Removed Commands
      Given the pytest test setup is prepared
      When docs do not reference removed commands is executed
      Then needle is not in text

    @bdd-command-example-linter-command-examples-in-docs-use-valid-commands @needs-review
    Example: Command Examples In Docs Use Valid Commands
      Given the pytest test setup is prepared
      When command examples in docs use valid commands is executed
      Then failures is falsy

    @bdd-command-example-linter-readme-skill-path-matches-repository @needs-review
    Example: Readme Skill Path Matches Repository
      Given the pytest test setup is prepared
      When readme skill path matches repository is executed
      Then 'skills/taskledger/SKILL.md' is in readme
      Then 'taskledger/skills/taskledger/SKILL.md' is not in readme
