@area-file_link_snapshots @feature-file-link-snapshots @generated @needs-review
Feature: File Link Snapshots

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-file-link-snapshots
  Rule: File Link Snapshots

    @bdd-file-link-snapshots-existing-links-load-without-baseline-fields @needs-review
    Example: Existing Links Load Without Baseline Fields
      Given the pytest test setup is prepared
      When existing links load without baseline fields is executed
      Then link.baseline_hash is None
      Then link.baseline_size is None
      Then link.baseline_mtime is None
      Then link.baseline_exists is None

    @bdd-file-link-snapshots-new-links-record-baseline-fields @needs-review
    Example: New Links Record Baseline Fields
      Given the pytest test setup is prepared
      When new links record baseline fields is executed
      Then result.exit_code equals 0
      Then link.baseline_exists is True
      Then link.target_type equals 'file'

    @bdd-file-link-snapshots-binary-files-hash-without-decoding-errors @needs-review
    Example: Binary Files Hash Without Decoding Errors
      Given the pytest test setup is prepared
      When binary files hash without decoding errors is executed
      Then result.exit_code equals 0

    @bdd-file-link-snapshots-modified-file-status @needs-review
    Example: Modified File Status
      Given the pytest test setup is prepared
      When modified file status is executed
      Then result.exit_code equals 0

    @bdd-file-link-snapshots-deleted-file-status @needs-review
    Example: Deleted File Status
      Given the pytest test setup is prepared
      When deleted file status is executed
      Then result.exit_code equals 0

    @bdd-file-link-snapshots-new-file-status-from-missing-baseline @needs-review
    Example: New File Status From Missing Baseline
      Given the pytest test setup is prepared
      When new file status from missing baseline is executed
      Then result.exit_code equals 0

    @bdd-file-link-snapshots-directory-status-is-unchanged-without-recursive-hashing @needs-review
    Example: Directory Status Is Unchanged Without Recursive Hashing
      Given the pytest test setup is prepared
      When directory status is unchanged without recursive hashing is executed
      Then result.exit_code equals 0

    @bdd-file-link-snapshots-refresh-rebaselines-modified-file @needs-review
    Example: Refresh Rebaselines Modified File
      Given the pytest test setup is prepared
      When refresh rebaselines modified file is executed
      Then refreshed.exit_code equals 0

    @bdd-file-link-snapshots-existing-link-baseline-is-preserved-without-explicit-snapshot @needs-review
    Example: Existing Link Baseline Is Preserved Without Explicit Snapshot
      Given the pytest test setup is prepared
      When existing link baseline is preserved without explicit snapshot is executed
      Then preserve.exit_code equals 0
      Then refresh.exit_code equals 0
