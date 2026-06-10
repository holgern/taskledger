@area-tree_command @feature-tree-command @generated @needs-review
Feature: Tree Command

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-tree-command
  Rule: Tree Command

    @bdd-tree-command-human-output-shows-no-tasks @needs-review
    Example: Human Output Shows No Tasks
      Given the pytest test setup is prepared
      When human output shows no tasks is executed
      Then result.exit_code equals 0
      Then 'TASKLEDGER TREE' is in result.output
      Then 'ledger main' is in result.output
      Then '(current)' is in result.output
      Then '(no tasks)' is in result.output

    @bdd-tree-command-shows-both-tasks @needs-review
    Example: Shows Both Tasks
      Given the pytest test setup is prepared
      When shows both tasks is executed
      Then result.exit_code equals 0
      Then 'task-0001' is in result.output
      Then 'task-0002' is in result.output
      Then 'parser-fix' is in result.output
      Then 'docs-cleanup' is in result.output
      Then '*' is in result.output

    @bdd-tree-command-no-active-task-still-succeeds @needs-review
    Example: No Active Task Still Succeeds
      Given the pytest test setup is prepared
      When no active task still succeeds is executed
      Then result.exit_code equals 0
      Then 'task-0001' is in result.output

    @bdd-tree-command-child-nested-under-parent-human @needs-review
    Example: Child Nested Under Parent Human
      Given the pytest test setup is prepared
      When child nested under parent human is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then 'task-0001' is in result.output
      Then 'task-0002' is in result.output
      Then '(follow-up)' is in result.output

    @bdd-tree-command-child-nested-under-parent-json @needs-review
    Example: Child Nested Under Parent Json
      Given the pytest test setup is prepared
      When child nested under parent json is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-tree-command-subtree-shows-only-selected @needs-review
    Example: Subtree Shows Only Selected
      Given the pytest test setup is prepared
      When subtree shows only selected is executed
      Then result.exit_code equals 0
      Then 'task-0001' is in result.output

    @bdd-tree-command-subtree-with-children @needs-review
    Example: Subtree With Children
      Given the pytest test setup is prepared
      When subtree with children is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-tree-command-details-shows-counts @needs-review
    Example: Details Shows Counts
      Given the pytest test setup is prepared
      When details shows counts is executed
      Then result.exit_code equals 0
      Then counts is not None
      Then 'todos' is in counts
      Then 'plans' is in counts
      Then 'runs' is in counts
      Then 'changes' is in counts
      Then 'has_lock' is in counts

    @bdd-tree-command-details-human-output-compact @needs-review
    Example: Details Human Output Compact
      Given the pytest test setup is prepared
      When details human output compact is executed
      Then result.exit_code equals 0

    @bdd-tree-command-all-ledgers-shows-multiple @needs-review
    Example: All Ledgers Shows Multiple
      Given the pytest test setup is prepared
      When all ledgers shows multiple is executed
      Then result.exit_code equals 0
      Then 'main' is in refs
      Then 'feature-a' is in refs

    @bdd-tree-command-all-ledgers-does-not-mutate-config @needs-review
    Example: All Ledgers Does Not Mutate Config
      Given the pytest test setup is prepared
      When all ledgers does not mutate config is executed
      Then result.exit_code equals 0
      Then config_before equals config_after

    @bdd-tree-command-current-ledger-release-is-rendered @needs-review
    Example: Current Ledger Release Is Rendered
      Given the pytest test setup is prepared
      When current ledger release is rendered is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then 'releases' is in result.output
      Then '0.1.0 -> task-0001' is in result.output

    @bdd-tree-command-all-ledgers-uses-each-ledger-release-records @needs-review
    Example: All Ledgers Uses Each Ledger Release Records
      Given the pytest test setup is prepared
      When all ledgers uses each ledger release records is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then result.exit_code equals 0

    @bdd-tree-command-plain-uses-ascii-glyphs @needs-review
    Example: Plain Uses Ascii Glyphs
      Given the pytest test setup is prepared
      When plain uses ascii glyphs is executed
      Then result.exit_code equals 0
      Then '├─' is not in result.output
      Then '└─' is not in result.output

    @bdd-tree-command-recorded-marker-in-output @needs-review
    Example: Recorded Marker In Output
      Given the pytest test setup is prepared
      When recorded marker in output is executed
      Then result.exit_code equals 0
      Then result.exit_code equals 0
      Then '{recorded}' is in result.output

    @bdd-tree-command-recorded-in-json @needs-review
    Example: Recorded In Json
      Given the pytest test setup is prepared
      When recorded in json is executed
      Then result.exit_code equals 0

    @bdd-tree-command-tree-hides-archived-by-default @needs-review
    Example: Tree Hides Archived By Default
      Given the pytest test setup is prepared
      When tree hides archived by default is executed
      Then result.exit_code equals 0
      Then archived.exit_code equals 0
      Then result.exit_code equals 0
      Then 'legacy' is not in result.output
      Then 'next=task-0002' is in result.output

    @bdd-tree-command-tree-include-archived-marks-nodes @needs-review
    Example: Tree Include Archived Marks Nodes
      Given the pytest test setup is prepared
      When tree include archived marks nodes is executed
      Then result.exit_code equals 0
      Then archived.exit_code equals 0
      Then result.exit_code equals 0
      Then 'legacy' is in result.output
      Then '{archived}' is in result.output
