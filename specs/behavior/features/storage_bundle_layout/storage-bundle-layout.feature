@area-storage_bundle_layout @feature-storage-bundle-layout @generated @needs-review
Feature: Storage Bundle Layout

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-storage-bundle-layout
  Rule: Storage Bundle Layout

    @bdd-storage-bundle-layout-task-create-uses-task-bundle-layout @needs-review
    Example: Task Create Uses Task Bundle Layout
      Given the pytest test setup is prepared
      When task create uses task bundle layout is executed
      Then result.exit_code equals 0

    @bdd-storage-bundle-layout-task-list-scans-task-markdown-without-indexes @needs-review
    Example: Task List Scans Task Markdown Without Indexes
      Given the pytest test setup is prepared
      When task list scans task markdown without indexes is executed
      Then result.exit_code equals 0
      Then 'scan-layout' is in result.stdout

    @bdd-storage-bundle-layout-task-list-ignores-removed-legacy-indexes @needs-review
    Example: Task List Ignores Removed Legacy Indexes
      Given the pytest test setup is prepared
      When task list ignores removed legacy indexes is executed
      Then result.exit_code equals 0
      Then 'legacy-indexes' is in result.stdout

    @bdd-storage-bundle-layout-task-create-no-orphan-slug-directory @needs-review
    Example: Task Create No Orphan Slug Directory
      Given the pytest test setup is prepared
      When task create no orphan slug directory is executed
      Then result.exit_code equals 0

    @bdd-storage-bundle-layout-repair-task-dirs-removes-orphans @needs-review
    Example: Repair Task Dirs Removes Orphans
      Given the pytest test setup is prepared
      When repair task dirs removes orphans is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then '1' is in result.stdout

    @bdd-storage-bundle-layout-list-plans-skips-malformed-plan-files @needs-review
    Example: List Plans Skips Malformed Plan Files
      Given the pytest test setup is prepared
      When list plans skips malformed plan files is executed
      Then result.exit_code equals 0

    @bdd-storage-bundle-layout-list-plans-loads-valid-plan-with-malformed-sibling @needs-review
    Example: List Plans Loads Valid Plan With Malformed Sibling
      Given the pytest test setup is prepared
      When list plans loads valid plan with malformed sibling is executed
      Then result.exit_code equals 0

    @bdd-storage-bundle-layout-rewrite-task-refs-updates-id-and-task-id @needs-review
    Example: Rewrite Task Refs Updates Id And Task Id
      Given the pytest test setup is prepared
      When rewrite task refs updates id and task id is executed
      Then result.exit_code equals 0

    @bdd-storage-bundle-layout-rewrite-task-refs-adds-missing-task-id @needs-review
    Example: Rewrite Task Refs Adds Missing Task Id
      Given the pytest test setup is prepared
      When rewrite task refs adds missing task id is executed
      Then result.exit_code equals 0

    @bdd-storage-bundle-layout-rewrite-task-refs-noop-on-same-id @needs-review
    Example: Rewrite Task Refs Noop On Same Id
      Given the pytest test setup is prepared
      When rewrite task refs noop on same id is executed
      Then result.exit_code equals 0
