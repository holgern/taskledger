@area-command_inventory @feature-command-inventory @generated @needs-review
Feature: Command Inventory

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-command-inventory
  Rule: Command Inventory

    @bdd-command-inventory-registered-commands-have-complete-metadata
    Example: Registered commands have complete inventory metadata
      Given the Taskledger CLI command tree is registered
      When command inventory metadata is inspected
      Then every registered command has an inventory entry and ledger effect

    @bdd-command-inventory-mutations-are-not-safe-read-only
    Example: Mutating commands are never classified safe read only
      Given a command can mutate ledger or workspace state
      When its inventory classification is inspected
      Then its effect is not safe_read_only

    @bdd-command-inventory-plan-review-is-classified-read-only @needs-review
    Example: Plan Review Is Classified Read Only
      Given the pytest test setup is prepared
      When plan review is classified read only is executed
      Then spec.effect equals 'safe_read_only'
      Then spec.ledger_effect equals EFFECT_READ
      Then spec.targeting equals TARGETING_ACTIVE_DEFAULT

    @bdd-command-inventory-lock-break-is-deprecated @needs-review
    Example: Lock Break Is Deprecated
      Given the pytest test setup is prepared
      When lock break is deprecated is executed
      Then spec.deprecated is True
      Then spec.replaced_by equals 'repair lock'
      Then spec.tier equals TIER_RARE

    @bdd-command-inventory-process-exec-commands @needs-review
    Example: Process Exec Commands
      Given the pytest test setup is prepared
      When process exec commands is executed
      Then 'implement command' is in process_cmds
      Then 'plan command' is in process_cmds

    @bdd-command-inventory-file-write-commands @needs-review
    Example: File Write Commands
      Given the pytest test setup is prepared
      When file write commands is executed
      Then 'export' is in file_write_cmds
      Then 'snapshot' is in file_write_cmds
      Then 'release changelog' is in file_write_cmds
      Then 'plan template' is in file_write_cmds

    @bdd-command-inventory-advanced-operations-are-not-in-agent-golden-path @needs-review
    Example: Advanced Operations Are Not In Agent Golden Path
      Given the pytest test setup is prepared
      When advanced operations are not in agent golden path is executed
      Then advanced_normal_work_exclusions.isdisjoint succeeds

    @bdd-command-inventory-repair-commands-remain-rare
    Example: Repair commands remain exceptional operations
      Given the command inventory contains normal and repair workflows
      When command tiers are inspected
      Then repair commands are classified in the rare tier

    @bdd-command-inventory-deprecated-hidden-by-default-in-commands-cli @needs-review
    Example: Deprecated Hidden By Default In Commands Cli
      Given the pytest test setup is prepared
      When deprecated hidden by default in commands cli is executed
      Then result.exit_code equals 0
      Then 'lock break' is not in result.stdout
      Then 'sync git pull' is in result.stdout
      Then 'sync git push' is in result.stdout
      Then 'sync git sync' is not in result.stdout
      Then result_with.exit_code equals 0
      Then 'lock break' is in result_with.stdout
      Then 'sync git pull' is in result_with.stdout
      Then 'sync git push' is in result_with.stdout
      Then 'sync git sync' is in result_with.stdout

    @bdd-command-inventory-tier-filter-in-commands-cli @needs-review
    Example: Tier Filter In Commands Cli
      Given the pytest test setup is prepared
      When tier filter in commands cli is executed
      Then result.exit_code equals 0

    @bdd-command-inventory-commands-json-includes-new-fields @needs-review
    Example: Commands Json Includes New Fields
      Given the pytest test setup is prepared
      When commands json includes new fields is executed
      Then result.exit_code equals 0
      Then field is in first

    @bdd-command-inventory-key-commands-have-stable-targeting
    Example: Key commands preserve their targeting contract
      Given task-scoped and workspace-scoped commands are inventoried
      When targeting metadata is inspected
      Then key commands retain their expected active-default or workspace targeting
