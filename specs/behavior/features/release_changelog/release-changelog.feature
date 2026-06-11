@area-release_changelog @feature-release-changelog @generated @needs-review
Feature: Release Changelog

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-release-changelog
  Rule: Release Changelog

    @bdd-release-changelog-release-tag-persists-release-record @needs-review
    Example: Release Tag Persists Release Record
      Given the pytest test setup is prepared
      When release tag persists release record is executed
      Then result.exit_code equals 0

    @bdd-release-changelog-release-tag-rejects-non-done-boundary @needs-review
    Example: Release Tag Rejects Non Done Boundary
      Given the pytest test setup is prepared
      When release tag rejects non done boundary is executed
      Then result.exit_code equals 0
      Then tag_result.exit_code does not equal 0

    @bdd-release-changelog-release-tag-rejects-duplicate-version @needs-review
    Example: Release Tag Rejects Duplicate Version
      Given the pytest test setup is prepared
      When release tag rejects duplicate version is executed
      Then result.exit_code does not equal 0

    @bdd-release-changelog-release-changelog-markdown-includes-instruction-and-evidence @needs-review
    Example: Release Changelog Markdown Includes Instruction And Evidence
      Given the pytest test setup is prepared
      When release changelog markdown includes instruction and evidence is executed
      Then result.exit_code equals 0
      Then expected_line is in result.stdout
      Then '## LLM instruction' is in result.stdout
      Then 'Improve dashboard refresh stability' is in result.stdout
      Then 'Implementation summary:' is in result.stdout
      Then 'Relevant changes:' is in result.stdout
      Then 'Evidence:' is in result.stdout
      Then "python -c print('ok')" is in result.stdout

    @bdd-release-changelog-release-changelog-from-task-is-inclusive @needs-review
    Example: Release Changelog From Task Is Inclusive
      Given the pytest test setup is prepared
      When release changelog from task is inclusive is executed
      Then first is in task_ids
      Then second is in task_ids

    @bdd-release-changelog-release-changelog-from-task-rejects-multiple-selectors @needs-review
    Example: Release Changelog From Task Rejects Multiple Selectors
      Given the pytest test setup is prepared
      When release changelog from task rejects multiple selectors is executed
      Then result.exit_code does not equal 0

    @bdd-release-changelog-release-changelog-fail-on-omitted @needs-review
    Example: Release Changelog Fail On Omitted
      Given the pytest test setup is prepared
      When release changelog fail on omitted is executed
      Then result.exit_code does not equal 0
      Then 'Omitted tasks found' is in omitted_text

    @bdd-release-changelog-release-changelog-include-status-implemented @needs-review
    Example: Release Changelog Include Status Implemented
      Given the pytest test setup is prepared
      When release changelog include status implemented is executed
      Then failed is in task_ids

    @bdd-release-changelog-release-changelog-target-changelog-and-release-date @needs-review
    Example: Release Changelog Target Changelog And Release Date
      Given the pytest test setup is prepared
      When release changelog target changelog and release date is executed
      Then md_result.exit_code equals 0
      Then '## Changelog edit guidance' is in md_result.stdout
      Then 'Target changelog: CHANGELOG.md' is in md_result.stdout
      Then 'Use release date: 2026-05-30' is in md_result.stdout
      Then md_result2.exit_code equals 0
      Then '## Changelog edit guidance' is not in md_result2.stdout

    @bdd-release-changelog-release-changelog-include-status-rejects-unknown @needs-review
    Example: Release Changelog Include Status Rejects Unknown
      Given the pytest test setup is prepared
      When release changelog include status rejects unknown is executed
      Then result.exit_code does not equal 0

    @bdd-release-changelog-release-list-sorts-by-boundary
    Example: Release listing is ordered by boundary task
      Given several release records exist at different task boundaries
      When releases are listed
      Then releases are ordered by their boundary tasks

    @bdd-release-changelog-release-show-returns-record
    Example: Release show returns the persisted release record
      Given a release record has been tagged
      When that release is shown
      Then its persisted version and boundary metadata are returned

    @bdd-release-changelog-default-filter-reports-omitted-tasks
    Example: Changelog defaults to done tasks and reports omissions
      Given a release range contains done and unfinished tasks
      When a changelog is generated with default status selection
      Then done tasks are included
      And omitted unfinished tasks are reported

    @bdd-release-changelog-bootstrap-since-task-is-supported
    Example: Changelog supports a bootstrap starting task
      Given no prior release boundary is available
      When changelog generation starts from an explicit task
      Then tasks from that bootstrap boundary are considered
