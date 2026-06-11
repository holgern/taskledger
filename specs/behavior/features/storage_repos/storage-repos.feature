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

    @bdd-storage-repos-repository-records-round-trip
    Example: Repository records persist and reload
      Given project repository records are configured
      When the repository collection is saved and loaded
      Then repository names, paths, kinds, and roles are preserved

    @bdd-storage-repos-invalid-repository-config-is-rejected
    Example: Invalid repository configuration is rejected
      Given a repository has a duplicate name, invalid type, or missing path
      When it is added to project repository configuration
      Then the repository is rejected

    @bdd-storage-repos-readonly-repo-cannot-be-execution-default
    Example: A readonly repository cannot be the execution default
      Given a configured repository is readonly
      When it is selected as the default execution repository
      Then the change is rejected

    @bdd-storage-repos-root-reference-resolves-project-root
    Example: The root repository reference resolves to the project root
      Given repository-aware project state
      When the root repository reference is resolved
      Then the project root is returned

    @bdd-storage-repos-unknown-reference-is-rejected
    Example: Unknown repository references are rejected
      Given a repository reference is not configured
      When Taskledger resolves the reference
      Then resolution fails with a not-found error
