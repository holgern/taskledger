@area-bdd_storage @feature-bdd-storage @generated @needs-review
Feature: Bdd Storage

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-bdd-storage
  Rule: Bdd Storage

    @bdd-bdd-storage-save-and-load-feature @needs-review
    Example: Save And Load Feature
      Given the pytest test setup is prepared
      When save and load feature is executed
      Then loaded is not None
      Then loaded.id equals 'feature-0001'
      Then loaded.title equals 'Task lifecycle gates'
      Then loaded.description equals 'Gates for task lifecycle'

    @bdd-bdd-storage-resolve-rule @needs-review
    Example: Resolve Rule
      Given the pytest test setup is prepared
      When resolve rule is executed
      Then resolved.id equals 'rule-0001'

    @bdd-bdd-storage-resolve-rule-normalized @needs-review
    Example: Resolve Rule Normalized
      Given the pytest test setup is prepared
      When resolve rule normalized is executed
      Then resolved.id equals 'rule-0001'

    @bdd-bdd-storage-resolve-example @needs-review
    Example: Resolve Example
      Given the pytest test setup is prepared
      When resolve example is executed
      Then resolved.id equals 'bdd-0001'

    @bdd-bdd-storage-resolve-example-normalized @needs-review
    Example: Resolve Example Normalized
      Given the pytest test setup is prepared
      When resolve example normalized is executed
      Then resolved.id equals 'bdd-0001'
