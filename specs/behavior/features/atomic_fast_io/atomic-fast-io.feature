@area-atomic_fast_io @feature-atomic-fast-io @generated @needs-review
Feature: Atomic Fast Io

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-atomic-fast-io
  Rule: Atomic Fast Io

    @bdd-atomic-fast-io-atomic-write-uses-fsync-by-default @needs-review
    Example: Atomic Write Uses Fsync By Default
      Given the pytest test setup is prepared
      When atomic write uses fsync by default is executed
      Then calls is truthy
