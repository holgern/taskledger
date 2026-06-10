@area-config_cli @feature-config-cli @generated @needs-review
Feature: Config Cli

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-config-cli
  Rule: Config Cli

    @bdd-config-cli-config-list-and-get-json @needs-review
    Example: Config List And Get Json
      Given the pytest test setup is prepared
      When config list and get json is executed
      Then listed.exit_code equals 0
      Then isinstance succeeds
      Then gotten.exit_code equals 0

    @bdd-config-cli-config-keys-lists-known-paths @needs-review
    Example: Config Keys Lists Known Paths
      Given the pytest test setup is prepared
      When config keys lists known paths is executed
      Then result.exit_code equals 0
      Then isinstance succeeds
      Then 'prompt_profiles.<profile>.plan_body_detail' is in key_names
      Then 'prompt_profiles.<profile>.question_policy' is in key_names
      Then 'default_memory_update_mode' is in key_names

    @bdd-config-cli-config-describe-shows-allowed-values-and-current-value @needs-review
    Example: Config Describe Shows Allowed Values And Current Value
      Given the pytest test setup is prepared
      When config describe shows allowed values and current value is executed
      Then set_result.exit_code equals 0
      Then describe_result.exit_code equals 0

    @bdd-config-cli-config-describe-unknown-key-returns-error @needs-review
    Example: Config Describe Unknown Key Returns Error
      Given the pytest test setup is prepared
      When config describe unknown key returns error is executed
      Then result.exit_code equals 1

    @bdd-config-cli-config-set-updates-prompt-profile-numbers @needs-review
    Example: Config Set Updates Prompt Profile Numbers
      Given the pytest test setup is prepared
      When config set updates prompt profile numbers is executed
      Then set_result.exit_code equals 0
      Then get_result.exit_code equals 0

    @bdd-config-cli-config-set-parses-bare-string-value @needs-review
    Example: Config Set Parses Bare String Value
      Given the pytest test setup is prepared
      When config set parses bare string value is executed
      Then set_result.exit_code equals 0
      Then get_result.exit_code equals 0

    @bdd-config-cli-config-set-rejects-invalid-values-with-json-error @needs-review
    Example: Config Set Rejects Invalid Values With Json Error
      Given the pytest test setup is prepared
      When config set rejects invalid values with json error is executed
      Then first_set.exit_code equals 0
      Then invalid_set.exit_code equals 1
      Then get_result.exit_code equals 0

    @bdd-config-cli-config-get-missing-key-returns-error @needs-review
    Example: Config Get Missing Key Returns Error
      Given the pytest test setup is prepared
      When config get missing key returns error is executed
      Then result.exit_code equals 1

    @bdd-config-cli-config-set-rejects-reserved-keys @needs-review
    Example: Config Set Rejects Reserved Keys
      Given the pytest test setup is prepared
      When config set rejects reserved keys is executed
      Then result.exit_code equals 1

    @bdd-config-cli-config-set-handles-inline-section-comments @needs-review
    Example: Config Set Handles Inline Section Comments
      Given the pytest test setup is prepared
      When config set handles inline section comments is executed
      Then result.exit_code equals 0
      Then '[prompt_profiles.planning] # keep note' is in updated
