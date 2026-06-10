@area-storage_init @feature-storage-init @generated @needs-review
Feature: Storage Init

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-storage-init
  Rule: Storage Init

    @bdd-storage-init-init-project-state-creates-structure @needs-review
    Example: Init Project State Creates Structure
      Given the pytest test setup is prepared
      When init project state creates structure is executed
      Then paths.project_dir.exists succeeds
      Then paths.config_path.exists succeeds
      Then paths.repo_index_path.exists succeeds

    @bdd-storage-init-ensure-project-exists-after-init @needs-review
    Example: Ensure Project Exists After Init
      Given the pytest test setup is prepared
      When ensure project exists after init is executed
      Then paths.workspace_root equals tmp_path

    @bdd-storage-init-init-creates-expected-directories @needs-review
    Example: Init Creates Expected Directories
      Given the pytest test setup is prepared
      When init creates expected directories is executed
      Then paths.releases_dir.is_dir succeeds
