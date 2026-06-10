@area-sync_git @feature-sync-git @generated @needs-review
Feature: Sync Git

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-sync-git
  Rule: Sync Git

    @bdd-sync-git-sync-git-help-promotes-pull-and-push @needs-review
    Example: Sync Git Help Promotes Pull And Push
      Given the pytest test setup is prepared
      When sync git help promotes pull and push is executed
      Then git_help.exit_code equals 0
      Then 'init' is in git_help.stdout
      Then 'status' is in git_help.stdout
      Then 'cd' is in git_help.stdout
      Then 'path' is in git_help.stdout
      Then 'commit' is in git_help.stdout
      Then 'import-local' is in git_help.stdout
      Then 'export-local' is in git_help.stdout
      Then 'pull' is in git_help.stdout
      Then 'push' is in git_help.stdout
      Then 'hooks' is in git_help.stdout
      Then hooks_help.exit_code equals 0
      Then 'install' is in hooks_help.stdout
      Then 'status' is in hooks_help.stdout
      Then 'uninstall' is in hooks_help.stdout

    @bdd-sync-git-sync-git-status-splits-project-and-outside-dirty-state @needs-review
    Example: Sync Git Status Splits Project And Outside Dirty State
      Given the pytest test setup is prepared
      When sync git status splits project and outside dirty state is executed
      Then result.exit_code equals 0
      Then any succeeds
      Then any succeeds

    @bdd-sync-git-sync-git-commit-ignores-unrelated-dirty-paths @needs-review
    Example: Sync Git Commit Ignores Unrelated Dirty Paths
      Given the pytest test setup is prepared
      When sync git commit ignores unrelated dirty paths is executed
      Then result.exit_code equals 0
      Then any succeeds
      Then 'project-a/local-note.txt' is in show
      Then 'project-b/other.txt' is not in show

    @bdd-sync-git-sync-git-export-local-remains-compatibility-alias @needs-review
    Example: Sync Git Export Local Remains Compatibility Alias
      Given the pytest test setup is prepared
      When sync git export local remains compatibility alias is executed
      Then result.exit_code equals 0

    @bdd-sync-git-sync-git-cd-and-path-report-expected-locations @needs-review
    Example: Sync Git Cd And Path Report Expected Locations
      Given the pytest test setup is prepared
      When sync git cd and path report expected locations is executed
      Then cd_result.exit_code equals 0
      Then cd_json.exit_code equals 0
      Then path_result.exit_code equals 0

    @bdd-sync-git-sync-git-pull-fails-fast-for-dirty-shared-repo @needs-review
    Example: Sync Git Pull Fails Fast For Dirty Shared Repo
      Given the pytest test setup is prepared
      When sync git pull fails fast for dirty shared repo is executed
      Then result.exit_code does not equal 0
      Then 'whole sync repository' is in output
      Then '--allow-dirty' is in output

    @bdd-sync-git-sync-git-push-commits-all-sync-repo-changes-and-pushes @needs-review
    Example: Sync Git Push Commits All Sync Repo Changes And Pushes
      Given the pytest test setup is prepared
      When sync git push commits all sync repo changes and pushes is executed
      Then result.exit_code equals 0
      Then any succeeds
      Then 'project-a/local-note.txt' is in pushed_files
      Then 'project-b/other.txt' is in pushed_files

    @bdd-sync-git-sync-git-pull-runs-git-pull-without-manual-cd @needs-review
    Example: Sync Git Pull Runs Git Pull Without Manual Cd
      Given the pytest test setup is prepared
      When sync git pull runs git pull without manual cd is executed
      Then result.exit_code equals 0

    @bdd-sync-git-sync-git-hooks-install-rejects-cross-project-managed-hook @needs-review
    Example: Sync Git Hooks Install Rejects Cross Project Managed Hook
      Given the pytest test setup is prepared
      When sync git hooks install rejects cross project managed hook is executed
      Then install_result.exit_code equals 0
      Then conflict_result.exit_code does not equal 0
