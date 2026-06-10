@area-storage_common @feature-storage-common @generated @needs-review
Feature: Storage Common

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-storage-common
  Rule: Storage Common

    @bdd-storage-common-summarize-text-long @needs-review
    Example: Summarize Text Long
      Given the pytest test setup is prepared
      When summarize text long is executed
      Then result is not None
      Then result.endswith succeeds

    @bdd-storage-common-content-hash-returns-sha256 @needs-review
    Example: Content Hash Returns Sha256
      Given the pytest test setup is prepared
      When content hash returns sha256 is executed
      Then h is not None

    @bdd-storage-common-merge-text-append @needs-review
    Example: Merge Text Append
      Given the pytest test setup is prepared
      When merge text append is executed
      Then result equals 'current\n\nincoming'

    @bdd-storage-common-merge-text-prepend @needs-review
    Example: Merge Text Prepend
      Given the pytest test setup is prepared
      When merge text prepend is executed
      Then result equals 'incoming\n\ncurrent'
