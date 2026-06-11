@area-storage_migration @feature-storage-migration @generated @needs-review
Feature: Storage Migration

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-storage-migration
  Rule: Storage Migration

    @bdd-storage-migration-storage-layout-version-is-3 @needs-review
    Example: Storage Layout Version Is 3
      Given the pytest test setup is prepared
      When storage layout version is 3 is executed
      Then TASKLEDGER_STORAGE_LAYOUT_VERSION equals 3

    @bdd-storage-migration-record-schema-version-matches-schema-version @needs-review
    Example: Record Schema Version Matches Schema Version
      Given the pytest test setup is prepared
      When record schema version matches schema version is executed
      Then TASKLEDGER_RECORD_SCHEMA_VERSION equals TASKLEDGER_SCHEMA_VERSION

    @bdd-storage-migration-schema-version-is-1 @needs-review
    Example: Schema Version Is 1
      Given the pytest test setup is prepared
      When schema version is 1 is executed
      Then TASKLEDGER_SCHEMA_VERSION equals 1

    @bdd-storage-migration-v2-file-version @needs-review
    Example: V2 File Version
      Given the pytest test setup is prepared
      When v2 file version is executed
      Then TASKLEDGER_V2_FILE_VERSION equals 'v2'

    @bdd-storage-migration-roundtrip @needs-review
    Example: Roundtrip
      Given the pytest test setup is prepared
      When roundtrip is executed
      Then loaded is not None
      Then loaded.storage_layout_version equals TASKLEDGER_STORAGE_LAYOUT_VERSION
      Then loaded.record_schema_version equals TASKLEDGER_RECORD_SCHEMA_VERSION
      Then loaded.created_with_taskledger equals '0.1.0'

    @bdd-storage-migration-to-dict-keys @needs-review
    Example: To Dict Keys
      Given the pytest test setup is prepared
      When to dict keys is executed
      Then 'storage_layout_version' is in d
      Then 'record_schema_version' is in d
      Then 'created_with_taskledger' is in d
      Then 'created_at' is in d

    @bdd-storage-migration-active-task-roundtrip-with-file-version @needs-review
    Example: Active Task Roundtrip With File Version
      Given the pytest test setup is prepared
      When active task roundtrip with file version is executed
      Then restored.file_version equals TASKLEDGER_V2_FILE_VERSION

    @bdd-storage-migration-active-task-legacy-no-file-version @needs-review
    Example: Active Task Legacy No File Version
      Given the pytest test setup is prepared
      When active task legacy no file version is executed
      Then state.file_version equals TASKLEDGER_V2_FILE_VERSION

    @bdd-storage-migration-todo-accepts-valid-v2 @needs-review
    Example: Todo Accepts Valid V2
      Given the pytest test setup is prepared
      When todo accepts valid v2 is executed
      Then todo.id equals 'todo-0001'

    @bdd-storage-migration-todo-accepts-legacy-no-version @needs-review
    Example: Todo Accepts Legacy No Version
      Given the pytest test setup is prepared
      When todo accepts legacy no version is executed
      Then todo.id equals 'todo-0001'

    @bdd-storage-migration-link-accepts-valid-v2 @needs-review
    Example: Link Accepts Valid V2
      Given the pytest test setup is prepared
      When link accepts valid v2 is executed
      Then link.path equals '/foo.py'

    @bdd-storage-migration-link-accepts-legacy-no-version @needs-review
    Example: Link Accepts Legacy No Version
      Given the pytest test setup is prepared
      When link accepts legacy no version is executed
      Then link.path equals '/foo.py'

    @bdd-storage-migration-requirement-accepts-valid-v2 @needs-review
    Example: Requirement Accepts Valid V2
      Given the pytest test setup is prepared
      When requirement accepts valid v2 is executed
      Then req.task_id equals 'task-0001'

    @bdd-storage-migration-requirement-accepts-legacy-no-version @needs-review
    Example: Requirement Accepts Legacy No Version
      Given the pytest test setup is prepared
      When requirement accepts legacy no version is executed
      Then req.task_id equals 'task-0001'

    @bdd-storage-migration-sidecars-reject-unsupported-record-versions
    Example: Sidecars reject unsupported record versions
      Given a persisted sidecar declares an unsupported schema or file version
      When Taskledger deserializes the sidecar
      Then loading fails with a version compatibility error

    @bdd-storage-migration-init-creates-storage-yaml @needs-review
    Example: Init Creates Storage Yaml
      Given the pytest test setup is prepared
      When init creates storage yaml is executed
      Then storage_yaml.exists succeeds
      Then any succeeds

    @bdd-storage-migration-migrate-status-no-storage @needs-review
    Example: Migrate Status No Storage
      Given the pytest test setup is prepared
      When migrate status no storage is executed
      Then result.exit_code equals 0
      Then 'No storage.yaml' is in result.output

    @bdd-storage-migration-migrate-status-up-to-date @needs-review
    Example: Migrate Status Up To Date
      Given the pytest test setup is prepared
      When migrate status up to date is executed
      Then result.exit_code equals 0
      Then 'up to date' is in result.output

    @bdd-storage-migration-migrate-plan-no-storage @needs-review
    Example: Migrate Plan No Storage
      Given the pytest test setup is prepared
      When migrate plan no storage is executed
      Then result.exit_code equals 0
      Then 'No storage.yaml' is in result.output

    @bdd-storage-migration-migrate-apply-no-storage @needs-review
    Example: Migrate Apply No Storage
      Given the pytest test setup is prepared
      When migrate apply no storage is executed
      Then result.exit_code equals 2

    @bdd-storage-migration-migrate-apply-up-to-date @needs-review
    Example: Migrate Apply Up To Date
      Given the pytest test setup is prepared
      When migrate apply up to date is executed
      Then result.exit_code equals 0
      Then 'up to date' is in result.output

    @bdd-storage-migration-migrate-commands-in-inventory @needs-review
    Example: Migrate Commands In Inventory
      Given the pytest test setup is prepared
      When migrate commands in inventory is executed
      Then 'migrate status' is in COMMAND_METADATA
      Then 'migrate plan' is in COMMAND_METADATA
      Then 'migrate apply' is in COMMAND_METADATA

    @bdd-storage-migration-doctor-schema-missing-storage-yaml @needs-review
    Example: Doctor Schema Missing Storage Yaml
      Given the pytest test setup is prepared
      When doctor schema missing storage yaml is executed
      Then any succeeds

    @bdd-storage-migration-inspect-records-for-migration-reports-malformed-markdown @needs-review
    Example: Inspect Records For Migration Reports Malformed Markdown
      Given the pytest test setup is prepared
      When inspect records for migration reports malformed markdown is executed
      Then any succeeds

    @bdd-storage-migration-doctor-schema-reports-malformed-task-record @needs-review
    Example: Doctor Schema Reports Malformed Task Record
      Given the pytest test setup is prepared
      When doctor schema reports malformed task record is executed
      Then any succeeds

    @bdd-storage-migration-migrate-apply-moves-legacy-unscoped-state-to-current-ledger @needs-review
    Example: Migrate Apply Moves Legacy Unscoped State To Current Ledger
      Given the pytest test setup is prepared
      When migrate apply moves legacy unscoped state to current ledger is executed
      Then 'branch-scoped-ledgers' is in applied
      Then meta is not None
      Then meta.storage_layout_version equals 3
      Then meta.last_migrated_with_taskledger is not None
      Then meta.last_migrated_at is not None
      Then match is not None
      Then next_num is at least 22

    @bdd-storage-migration-migrate-apply-noop-for-already-branch-scoped-v2-workspace @needs-review
    Example: Migrate Apply Noop For Already Branch Scoped V2 Workspace
      Given the pytest test setup is prepared
      When migrate apply noop for already branch scoped v2 workspace is executed
      Then 'branch-scoped-ledgers' is in applied
      Then meta is not None
      Then meta.storage_layout_version equals 3

    @bdd-storage-migration-status-detects-branch-scoped-migration
    Example: Migration status detects legacy unscoped state
      Given a layout version 2 workspace contains legacy root task state
      When Taskledger determines the required layout migrations
      Then the branch-scoped-ledgers migration from version 2 to version 3 is required

    @bdd-storage-migration-migrate-renumbers-older-root-task-on-conflict @needs-review
    Example: Migrate Renumbers Older Root Task On Conflict
      Given the pytest test setup is prepared
      When migrate renumbers older root task on conflict is executed
      Then 'Root Task' is in root_content
      Then 'id: task-0001' is in root_content
      Then 'Ledger Task' is in ledger_content
      Then 'id: task-0002' is in ledger_content

    @bdd-storage-migration-migrate-preserves-task-timestamps-after-renumbering @needs-review
    Example: Migrate Preserves Task Timestamps After Renumbering
      Given the pytest test setup is prepared
      When migrate preserves task timestamps after renumbering is executed
      Then '2026-01-01 12:34:56' is in root_content
      Then 'id: task-0001' is in root_content
      Then 'Original Task' is in root_content
      Then 'id: task-0002' is in ledger_content
      Then 'Ledger Task' is in ledger_content

    @bdd-storage-migration-migrate-renumbers-multiple-task-id-conflicts
    Example: Migration renumbers multiple task ID conflicts deterministically
      Given legacy root tasks conflict with newer ledger tasks at several task IDs
      When the branch-scoped-ledgers migration is applied
      Then older root tasks retain the lower task IDs
      And newer ledger tasks receive consecutive higher task IDs

    @bdd-storage-migration-migrate-rebuilds-ledger-indexes
    Example: Migration removes legacy indexes and rebuilds ledger indexes
      Given a layout version 2 workspace contains legacy root indexes
      When the branch-scoped-ledgers migration is applied
      Then the legacy root indexes are removed
      And the current ledger indexes are rebuilt

    @bdd-storage-migration-migrate-merges-active-task-keeping-newer @needs-review
    Example: Migrate Merges Active Task Keeping Newer
      Given the pytest test setup is prepared
      When migrate merges active task keeping newer is executed
      Then 'task-0005' is in result_content
      Then '2026-04-25' is in result_content

    @bdd-storage-migration-migrate-merges-active-task-from-root-if-newer @needs-review
    Example: Migrate Merges Active Task From Root If Newer
      Given the pytest test setup is prepared
      When migrate merges active task from root if newer is executed
      Then 'task-0003' is in result_content
      Then '2026-04-28' is in result_content
