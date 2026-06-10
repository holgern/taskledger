@area-locks_audit @feature-locks-audit @generated @needs-review
Feature: Locks Audit

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-locks-audit
  Rule: Locks Audit

    @bdd-locks-audit-break-lock-writes-audit-file-and-repair-event @needs-review
    Example: Break Lock Writes Audit File And Repair Event
      Given the pytest test setup is prepared
      When break lock writes audit file and repair event is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-locks-audit-stale-lock-blocks-new-run-until-explicit-break @needs-review
    Example: Stale Lock Blocks New Run Until Explicit Break
      Given the pytest test setup is prepared
      When stale lock blocks new run until explicit break is executed
      Then blocked.exit_code does not equal 0
