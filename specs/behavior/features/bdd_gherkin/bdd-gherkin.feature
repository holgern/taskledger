@area-bdd_gherkin @feature-bdd-gherkin @generated @needs-review
Feature: Bdd Gherkin

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-bdd-gherkin
  Rule: Bdd Gherkin

    @bdd-bdd-gherkin-export-basic-feature @needs-review
    Example: Export Basic Feature
      Given the pytest test setup is prepared
      When export basic feature is executed
      Then out.exists succeeds
      Then 'Feature: Task lifecycle gates' is in content
      Then 'Rule: Implementation requires an accepted plan' is in content
      Then 'Scenario: Agent tries to implement before approval' is in content
      Then 'Given a task has a proposed plan' is in content
      Then 'And the plan has not been approved' is in content
      Then 'When the agent starts implementation' is in content
      Then 'Then implementation is blocked' is in content

    @bdd-bdd-gherkin-export-ownership-header @needs-review
    Example: Export Ownership Header
      Given the pytest test setup is prepared
      When export ownership header is executed
      Then '# Generated derived output from Taskledger task task-0001.' is in content
      Then '# Prefer SpecWeave-owned specs/behavior/features/' is in content
      Then '# Plain pytest files under tests/' is in content

    @bdd-bdd-gherkin-export-warns-for-deprecated-output-paths @needs-review
    Example: Export Warns For Deprecated Output Paths
      Given the pytest test setup is prepared
      When export warns for deprecated output paths is executed
      Then out.exists succeeds
      Then any succeeds
      Then any succeeds

    @bdd-bdd-gherkin-export-with-tags @needs-review
    Example: Export With Tags
      Given the pytest test setup is prepared
      When export with tags is executed
      Then feature is not None
      Then '@lifecycle' is in content
      Then '@gates' is in content

    @bdd-bdd-gherkin-export-requires-formulated-examples
    Example: Gherkin export requires formulated examples
      Given behavior state has no formulated examples
      When Gherkin export is requested
      Then export is rejected

    @bdd-bdd-gherkin-export-stays-inside-workspace
    Example: Gherkin export stays inside the workspace
      Given an export path points outside the project workspace
      When Gherkin export is requested
      Then export is rejected

    @bdd-bdd-gherkin-export-order-is-deterministic
    Example: Gherkin export ordering is deterministic
      Given behavior rules and examples have stable identifiers
      When Gherkin is exported repeatedly
      Then the generated ordering is stable

    @bdd-bdd-gherkin-export-requires-initialized-behavior-state
    Example: Gherkin export requires initialized behavior state
      Given behavior state has not been initialized
      When Gherkin export is requested
      Then export fails with a clear initialization error
