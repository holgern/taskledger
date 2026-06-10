@area-command_runner @feature-command-runner @generated @needs-review
Feature: Command Runner

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-command-runner
  Rule: Command Runner

    @bdd-command-runner-run-command-preserves-nonzero-python-exit-code @needs-review
    Example: Run Command Preserves Nonzero Python Exit Code
      Given the pytest test setup is prepared
      When run command preserves nonzero python exit code is executed
      Then result.returncode equals 3
      Then result.stdout equals ''
      Then result.stderr equals ''

    @bdd-command-runner-run-command-preserves-zero-python-exit-code @needs-review
    Example: Run Command Preserves Zero Python Exit Code
      Given the pytest test setup is prepared
      When run command preserves zero python exit code is executed
      Then result.returncode equals 0
      Then result.stdout equals ''
      Then result.stderr equals ''
