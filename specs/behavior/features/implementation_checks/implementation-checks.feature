@area-implementation_checks @feature-implementation-checks @generated @needs-review
Feature: Implementation Checks

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-implementation-checks
  Rule: Implementation Checks

    @bdd-implementation-checks-to-dict-from-dict-round-trip @needs-review
    Example: To Dict From Dict Round Trip
      Given the pytest test setup is prepared
      When to dict from dict round trip is executed
      Then restored equals record

    @bdd-implementation-checks-defaults @needs-review
    Example: Defaults
      Given the pytest test setup is prepared
      When defaults is executed
      Then record.status equals 'unknown'
      Then record.category equals 'other'
      Then record.exit_code is None
      Then record.summary is None

    @bdd-implementation-checks-creates-check-not-change @needs-review
    Example: Creates Check Not Change
      Given the pytest test setup is prepared
      When creates check not change is executed
      Then r.exit_code equals 0

    @bdd-implementation-checks-check-has-category @needs-review
    Example: Check Has Category
      Given the pytest test setup is prepared
      When check has category is executed
      Then r.exit_code equals 0

    @bdd-implementation-checks-check-refs-on-run @needs-review
    Example: Check Refs On Run
      Given the pytest test setup is prepared
      When check refs on run is executed
      Then r.exit_code equals 0
      Then check_id is in run.check_refs

    @bdd-implementation-checks-human-output-shows-check @needs-review
    Example: Human Output Shows Check
      Given the pytest test setup is prepared
      When human output shows check is executed
      Then r.exit_code equals 0
      Then 'recorded check check-' is in r.output

    @bdd-implementation-checks-failed-command-creates-failed-check @needs-review
    Example: Failed Command Creates Failed Check
      Given the pytest test setup is prepared
      When failed command creates failed check is executed
      Then r.exit_code equals 1

    @bdd-implementation-checks-allow-failure-records-check @needs-review
    Example: Allow Failure Records Check
      Given the pytest test setup is prepared
      When allow failure records check is executed
      Then r.exit_code equals 0
