@area-legacy_cleanup_contracts @feature-legacy-cleanup-contracts @generated @needs-review
Feature: Legacy Cleanup Contracts

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-legacy-cleanup-contracts
  Rule: Legacy Cleanup Contracts

    @bdd-legacy-cleanup-contracts-package-initializers-do-not-use-star-imports @needs-review
    Example: Package Initializers Do Not Use Star Imports
      Given the pytest test setup is prepared
      When package initializers do not use star imports is executed
      Then 'import *' is not in text

    @bdd-legacy-cleanup-contracts-v2-storage-does-not-import-storage-facade @needs-review
    Example: V2 Storage Does Not Import Storage Facade
      Given the pytest test setup is prepared
      When v2 storage does not import storage facade is executed
      Then 'from taskledger.storage import' is not in text

    @bdd-legacy-cleanup-contracts-domain-models-does-not-import-legacy-models-package @needs-review
    Example: Domain Models Does Not Import Legacy Models Package
      Given the pytest test setup is prepared
      When domain models does not import legacy models package is executed
      Then 'from taskledger.models import' is not in text
