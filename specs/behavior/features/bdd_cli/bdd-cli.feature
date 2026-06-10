@area-bdd_cli @feature-bdd-cli @generated @needs-review
Feature: Bdd Cli

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-bdd-cli
  Rule: Bdd Cli

    @bdd-bdd-cli-bdd-init-json @needs-review
    Example: Bdd Init Json
      Given the pytest test setup is prepared
      When bdd init json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-bdd-init-human @needs-review
    Example: Bdd Init Human
      Given the pytest test setup is prepared
      When bdd init human is executed
      Then result.exit_code equals 0
      Then 'BDD initialized' is in result.stdout

    @bdd-bdd-cli-bdd-init-twice-fails @needs-review
    Example: Bdd Init Twice Fails
      Given the pytest test setup is prepared
      When bdd init twice fails is executed
      Then result.exit_code does not equal 0

    @bdd-bdd-cli-bdd-status-json @needs-review
    Example: Bdd Status Json
      Given the pytest test setup is prepared
      When bdd status json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-rule-add-json @needs-review
    Example: Rule Add Json
      Given the pytest test setup is prepared
      When rule add json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-rule-list-json @needs-review
    Example: Rule List Json
      Given the pytest test setup is prepared
      When rule list json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-rule-show-json @needs-review
    Example: Rule Show Json
      Given the pytest test setup is prepared
      When rule show json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-example-add-json @needs-review
    Example: Example Add Json
      Given the pytest test setup is prepared
      When example add json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-example-list-json @needs-review
    Example: Example List Json
      Given the pytest test setup is prepared
      When example list json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-example-show-json @needs-review
    Example: Example Show Json
      Given the pytest test setup is prepared
      When example show json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-example-link-ac @needs-review
    Example: Example Link Ac
      Given the pytest test setup is prepared
      When example link ac is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-gherkin-export-json @needs-review
    Example: Gherkin Export Json
      Given the pytest test setup is prepared
      When gherkin export json is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-gherkin-export-warns-for-deprecated-paths @needs-review
    Example: Gherkin Export Warns For Deprecated Paths
      Given the pytest test setup is prepared
      When gherkin export warns for deprecated paths is executed
      Then result.exit_code equals 0
      Then any succeeds
      Then any succeeds

    @bdd-bdd-cli-export-json-includes-external-behavior-spec-metadata @needs-review
    Example: Export Json Includes External Behavior Spec Metadata
      Given the pytest test setup is prepared
      When export json includes external behavior spec metadata is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-archledger-candidate @needs-review
    Example: Archledger Candidate
      Given the pytest test setup is prepared
      When archledger candidate is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-example-link-archledger @needs-review
    Example: Example Link Archledger
      Given the pytest test setup is prepared
      When example link archledger is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-link-automation-then-candidate-includes-feature-file @needs-review
    Example: Link Automation Then Candidate Includes Feature File
      Given the pytest test setup is prepared
      When link automation then candidate includes feature file is executed
      Then link_result.exit_code equals 0
      Then result.exit_code equals 0
      Then feature_file is in content
      Then 'tests/test_task_management_plan_gates.py' is in content
      Then pytest_ref is in content
      Then 'source_refs:' is in content
      Then 'test_refs:' is in content
      Then 'automation:' is in content

    @bdd-bdd-cli-link-automation-rejects-non-canonical-feature-path @needs-review
    Example: Link Automation Rejects Non Canonical Feature Path
      Given the pytest test setup is prepared
      When link automation rejects non canonical feature path is executed
      Then result.exit_code does not equal 0

    @bdd-bdd-cli-example-add-unknown-rule-fails @needs-review
    Example: Example Add Unknown Rule Fails
      Given the pytest test setup is prepared
      When example add unknown rule fails is executed
      Then result.exit_code does not equal 0

    @bdd-bdd-cli-example-add-unknown-criterion-with-accepted-plan-fails @needs-review
    Example: Example Add Unknown Criterion With Accepted Plan Fails
      Given the pytest test setup is prepared
      When example add unknown criterion with accepted plan fails is executed
      Then result.exit_code does not equal 0

    @bdd-bdd-cli-example-add-known-criterion-with-accepted-plan-succeeds @needs-review
    Example: Example Add Known Criterion With Accepted Plan Succeeds
      Given the pytest test setup is prepared
      When example add known criterion with accepted plan succeeds is executed
      Then result.exit_code equals 0

    @bdd-bdd-cli-example-add-criterion-without-plan-warns @needs-review
    Example: Example Add Criterion Without Plan Warns
      Given the pytest test setup is prepared
      When example add criterion without plan warns is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-bdd-cli-link-ac-unknown-criterion-with-accepted-plan-fails @needs-review
    Example: Link Ac Unknown Criterion With Accepted Plan Fails
      Given the pytest test setup is prepared
      When link ac unknown criterion with accepted plan fails is executed
      Then result.exit_code does not equal 0
