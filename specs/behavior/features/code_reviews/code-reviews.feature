@area-code_reviews @feature-code-reviews @generated @needs-review
Feature: Code Reviews

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-code-reviews
  Rule: Code Reviews

    @bdd-code-reviews-code-review-record-round-trip @needs-review
    Example: Code Review Record Round Trip
      Given the pytest test setup is prepared
      When code review record round trip is executed
      Then loaded.review_id equals 'review-0001'
      Then loaded.result equals 'pass'
      Then loaded.source equals 'working_tree'

    @bdd-code-reviews-storage-save-list-resolve-code-reviews @needs-review
    Example: Storage Save List Resolve Code Reviews
      Given the pytest test setup is prepared
      When storage save list resolve code reviews is executed
      Then resolved.review_id equals 'review-0001'

    @bdd-code-reviews-service-records-and-lists-manual-review @needs-review
    Example: Service Records And Lists Manual Review
      Given the pytest test setup is prepared
      When service records and lists manual review is executed
      Then review.review_id equals 'review-0001'
      Then review.source equals 'manual'
      Then shown.body equals 'No blocking issues.'

    @bdd-code-reviews-service-records-review-after-task-is-done @needs-review
    Example: Service Records Review After Task Is Done
      Given the pytest test setup is prepared
      When service records review after task is done is executed
      Then review.review_id equals 'review-0001'
      Then review.implementation_run is not None
      Then shown.body equals 'Post-completion code review.'

    @bdd-code-reviews-service-records-working-tree-git-metadata @needs-review
    Example: Service Records Working Tree Git Metadata
      Given the pytest test setup is prepared
      When service records working tree git metadata is executed
      Then review.source equals 'working_tree'
      Then review.git_status_short is not None
      Then review.git_diff_hash is not None
      Then review.git_diff_hash.startswith succeeds
      Then 'sample.txt' is in review.git_changed_paths

    @bdd-code-reviews-service-records-commit-git-metadata @needs-review
    Example: Service Records Commit Git Metadata
      Given the pytest test setup is prepared
      When service records commit git metadata is executed
      Then review.source equals 'commit'
      Then review.git_commit is not None
      Then 'sample.txt' is in review.git_changed_paths

    @bdd-code-reviews-cli-review-record-list-show-and-json @needs-review
    Example: Cli Review Record List Show And Json
      Given the pytest test setup is prepared
      When cli review record list show and json is executed
      Then 'review-0001' is in list_result.stdout
      Then 'Looks good.' is in show_result.stdout

    @bdd-code-reviews-cli-review-record-summary-and-file-are-mutually-exclusive @needs-review
    Example: Cli Review Record Summary And File Are Mutually Exclusive
      Given the pytest test setup is prepared
      When cli review record summary and file are mutually exclusive is executed
      Then result.exit_code does not equal 0
      Then 'Use either --summary or --summary-file' is in stderr
