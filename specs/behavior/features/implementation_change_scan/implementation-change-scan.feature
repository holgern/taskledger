@area-implementation_change_scan @feature-implementation-change-scan @generated @needs-review
Feature: Implementation Change Scan

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-implementation-change-scan
  Rule: Implementation Change Scan

    @bdd-implementation-change-scan-scan-changes-from-git-records-branch-status-and-diff-stat @needs-review
    Example: Scan Changes From Git Records Branch Status And Diff Stat
      Given the pytest test setup is prepared
      When scan changes from git records branch status and diff stat is executed
      Then result.exit_code equals 0

    @bdd-implementation-change-scan-scan-changes-from-git-rejects-non-git-workspace @needs-review
    Example: Scan Changes From Git Rejects Non Git Workspace
      Given the pytest test setup is prepared
      When scan changes from git rejects non git workspace is executed
      Then result.exit_code does not equal 0

    @bdd-implementation-change-scan-manual-implement-change-still-works-via-canonical-command @needs-review
    Example: Manual Implement Change Still Works Via Canonical Command
      Given the pytest test setup is prepared
      When manual implement change still works via canonical command is executed
      Then result.exit_code equals 0

    @bdd-implementation-change-scan-implement-finish-warns-when-git-scan-missing @needs-review
    Example: Implement Finish Warns When Git Scan Missing
      Given the pytest test setup is prepared
      When implement finish warns when git scan missing is executed
      Then manual.exit_code equals 0
      Then finish.exit_code equals 0
      Then isinstance succeeds
      Then any succeeds

    @bdd-implementation-change-scan-implement-finish-warning-clears-after-git-scan @needs-review
    Example: Implement Finish Warning Clears After Git Scan
      Given the pytest test setup is prepared
      When implement finish warning clears after git scan is executed
      Then finish.exit_code equals 0
      Then isinstance succeeds
