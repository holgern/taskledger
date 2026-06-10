@area-bdd_models @feature-bdd-models @generated @needs-review
Feature: Bdd Models

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-bdd-models
  Rule: Bdd Models

    @bdd-bdd-models-defaults @needs-review
    Example: Defaults
      Given the pytest test setup is prepared
      When defaults is executed
      Then ref.status equals 'pending'
      Then ref.feature_file equals ''
      Then ref.scenario equals ''
      Then ref.pytest_path equals ''
      Then ref.pytest_nodeid equals ''
      Then ref.command equals ''
      Then ref.report_path equals ''

    @bdd-bdd-models-round-trip @needs-review
    Example: Round Trip
      Given the pytest test setup is prepared
      When round trip is executed
      Then restored equals ref

    @bdd-bdd-models-from-dict-none @needs-review
    Example: From Dict None
      Given the pytest test setup is prepared
      When from dict none is executed
      Then ref.status equals 'pending'

    @bdd-bdd-models-defaults-2 @needs-review
    Example: Defaults
      Given the pytest test setup is prepared
      When defaults is executed
      Then rec.object_type equals 'bdd_feature'
      Then rec.description equals ''

    @bdd-bdd-models-round-trip-2 @needs-review
    Example: Round Trip
      Given the pytest test setup is prepared
      When round trip is executed
      Then restored equals rec

    @bdd-bdd-models-defaults-3 @needs-review
    Example: Defaults
      Given the pytest test setup is prepared
      When defaults is executed
      Then rec.object_type equals 'bdd_rule'
      Then rec.feature_id equals 'bdd'
      Then rec.source equals 'user'

    @bdd-bdd-models-round-trip-3 @needs-review
    Example: Round Trip
      Given the pytest test setup is prepared
      When round trip is executed
      Then restored equals rec

    @bdd-bdd-models-defaults-4 @needs-review
    Example: Defaults
      Given the pytest test setup is prepared
      When defaults is executed
      Then rec.object_type equals 'bdd_example'
      Then rec.status equals 'discovered'
      Then rec.automation.status equals 'pending'

    @bdd-bdd-models-round-trip-4 @needs-review
    Example: Round Trip
      Given the pytest test setup is prepared
      When round trip is executed
      Then restored equals rec

    @bdd-bdd-models-defaults-5 @needs-review
    Example: Defaults
      Given the pytest test setup is prepared
      When defaults is executed
      Then rec.object_type equals 'bdd_report'
      Then rec.result equals 'unknown'

    @bdd-bdd-models-round-trip-5 @needs-review
    Example: Round Trip
      Given the pytest test setup is prepared
      When round trip is executed
      Then restored equals rec
