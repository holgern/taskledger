@area-storage_sync @feature-storage-sync @generated @needs-review
Feature: Storage Sync

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-storage-sync
  Rule: Storage Sync

    @bdd-storage-sync-storage-where-reports-external-storage-details @needs-review
    Example: Storage Where Reports External Storage Details
      Given the pytest test setup is prepared
      When storage where reports external storage details is executed
      Then init_result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-storage-sync-storage-move-copy-updates-config-and-preserves-project-uuid @needs-review
    Example: Storage Move Copy Updates Config And Preserves Project Uuid
      Given the pytest test setup is prepared
      When storage move copy updates config and preserves project uuid is executed
      Then init_result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-storage-sync-storage-move-refuses-non-empty-target @needs-review
    Example: Storage Move Refuses Non Empty Target
      Given the pytest test setup is prepared
      When storage move refuses non empty target is executed
      Then init_result.exit_code equals 0
      Then result.exit_code does not equal 0

    @bdd-storage-sync-sync-preflight-is-read-only-and-warns-about-active-locks @needs-review
    Example: Sync Preflight Is Read Only And Warns About Active Locks
      Given the pytest test setup is prepared
      When sync preflight is read only and warns about active locks is executed
      Then result.exit_code equals 0
      Then before equals after
      Then any succeeds

    @bdd-storage-sync-sync-preflight-warns-when-in-repo-storage-is-tracked @needs-review
    Example: Sync Preflight Warns When In Repo Storage Is Tracked
      Given the pytest test setup is prepared
      When sync preflight warns when in repo storage is tracked is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-storage-sync-sync-status-reports-git-changes-for-external-state-repo @needs-review
    Example: Sync Status Reports Git Changes For External State Repo
      Given the pytest test setup is prepared
      When sync status reports git changes for external state repo is executed
      Then result.exit_code equals 0

    @bdd-storage-sync-sync-commit-commits-external-state-repo @needs-review
    Example: Sync Commit Commits External State Repo
      Given the pytest test setup is prepared
      When sync commit commits external state repo is executed
      Then result.exit_code equals 0

    @bdd-storage-sync-sync-help-includes-aliases-and-git-group @needs-review
    Example: Sync Help Includes Aliases And Git Group
      Given the pytest test setup is prepared
      When sync help includes aliases and git group is executed
      Then result.exit_code equals 0
      Then 'preflight' is in result.stdout
      Then 'status' is in result.stdout
      Then 'commit' is in result.stdout
      Then 'export' is in result.stdout
      Then 'import' is in result.stdout
      Then 'git' is in result.stdout

    @bdd-storage-sync-sync-export-alias-writes-archive @needs-review
    Example: Sync Export Alias Writes Archive
      Given the pytest test setup is prepared
      When sync export alias writes archive is executed
      Then root_result.exit_code equals 0
      Then sync_result.exit_code equals 0
      Then root_archive.exists succeeds
      Then sync_archive.exists succeeds

    @bdd-storage-sync-export-conflicting-output-args-include-command-specific-hint @needs-review
    Example: Export Conflicting Output Args Include Command Specific Hint
      Given the pytest test setup is prepared
      When export conflicting output args include command specific hint is executed
      Then root_result.exit_code equals 2
      Then sync_result.exit_code equals 2
