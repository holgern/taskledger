@area-storage_repos @feature-storage-repos @generated @needs-review
Feature: Storage Repos

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-storage-repos
  Rule: Storage Repos

    @bdd-storage-repos-add-repo @needs-review
    Example: Add Repo
      Given the pytest test setup is prepared
      When add repo is executed
      Then repo.name equals 'my-code'
      Then repo.slug equals 'my-code'

    @bdd-storage-repos-resolve-repo @needs-review
    Example: Resolve Repo
      Given the pytest test setup is prepared
      When resolve repo is executed
      Then found.name equals 'my-code'

    @bdd-storage-repos-resolve-repo-by-slugified-ref @needs-review
    Example: Resolve Repo By Slugified Ref
      Given the pytest test setup is prepared
      When resolve repo by slugified ref is executed
      Then found.name equals 'My Code'

    @bdd-storage-repos-remove-repo @needs-review
    Example: Remove Repo
      Given the pytest test setup is prepared
      When remove repo is executed
      Then removed.name equals 'my-code'

    @bdd-storage-repos-set-repo-role @needs-review
    Example: Set Repo Role
      Given the pytest test setup is prepared
      When set repo role is executed
      Then updated.role equals 'both'

    @bdd-storage-repos-set-default-execution-repo @needs-review
    Example: Set Default Execution Repo
      Given the pytest test setup is prepared
      When set default execution repo is executed
      Then result.preferred_for_execution is True

    @bdd-storage-repos-clear-default-execution-repo @needs-review
    Example: Clear Default Execution Repo
      Given the pytest test setup is prepared
      When clear default execution repo is executed
      Then all succeeds
