@area-task_markdown_export @feature-task-markdown-export @generated @needs-review
Feature: Task Markdown Export

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-task-markdown-export
  Rule: Task Markdown Export

    @bdd-task-markdown-export-task-export-includes-curated-report-and-raw-task-files @needs-review
    Example: Task Export Includes Curated Report And Raw Task Files
      Given the pytest test setup is prepared
      When task export includes curated report and raw task files is executed
      Then isinstance succeeds
      Then '# Compiled Task Export:' is in content
      Then '## Curated Task Report' is in content
      Then '## Raw Taskledger Record Files' is in content
      Then 'task.md' is in content
      Then 'plans/' is in content
      Then isinstance succeeds

    @bdd-task-markdown-export-task-export-includes-source-file-snapshots-from-changes @needs-review
    Example: Task Export Includes Source File Snapshots From Changes
      Given the pytest test setup is prepared
      When task export includes source file snapshots from changes is executed
      Then isinstance succeeds
      Then '## Source File Snapshots' is in content
      Then '# Test Project' is in content

    @bdd-task-markdown-export-task-export-no-source-files-skips-source-snapshot-section @needs-review
    Example: Task Export No Source Files Skips Source Snapshot Section
      Given the pytest test setup is prepared
      When task export no source files skips source snapshot section is executed
      Then isinstance succeeds
      Then '## Source File Snapshots' is not in content
      Then '# Test Project' is not in content

    @bdd-task-markdown-export-task-export-skips-outside-workspace-file @needs-review
    Example: Task Export Skips Outside Workspace File
      Given the pytest test setup is prepared
      When task export skips outside workspace file is executed
      Then isinstance succeeds
      Then isinstance succeeds
      Then '/etc/passwd' is in paths

    @bdd-task-markdown-export-task-export-skips-oversized-source-file @needs-review
    Example: Task Export Skips Oversized Source File
      Given the pytest test setup is prepared
      When task export skips oversized source file is executed
      Then isinstance succeeds
      Then isinstance succeeds
      Then 'bigfile.txt' is in reasons_by_path

    @bdd-task-markdown-export-task-export-does-not-mutate-taskledger-state @needs-review
    Example: Task Export Does Not Mutate Taskledger State
      Given the pytest test setup is prepared
      When task export does not mutate taskledger state is executed
      Then before equals after

    @bdd-task-markdown-export-task-export-front-matter-contains-metadata @needs-review
    Example: Task Export Front Matter Contains Metadata
      Given the pytest test setup is prepared
      When task export front matter contains metadata is executed
      Then isinstance succeeds
      Then 'object_type: task_markdown_export' is in content
      Then 'export_version: 1' is in content
      Then 'taskledger_version:' is in content
      Then 'include_source_files: True' is in content

    @bdd-task-markdown-export-task-export-deterministic-body @needs-review
    Example: Task Export Deterministic Body
      Given the pytest test setup is prepared
      When task export deterministic body is executed
      Then isinstance succeeds
      Then isinstance succeeds
      Then body1 equals body2

    @bdd-task-markdown-export-task-export-summary-table @needs-review
    Example: Task Export Summary Table
      Given the pytest test setup is prepared
      When task export summary table is executed
      Then isinstance succeeds
      Then '## Export Summary' is in content
      Then '| Record files included |' is in content
      Then '| Source files included |' is in content

    @bdd-task-markdown-export-task-export-dedupes-change-and-plan-source-paths @needs-review
    Example: Task Export Dedupes Change And Plan Source Paths
      Given the pytest test setup is prepared
      When task export dedupes change and plan source paths is executed
      Then isinstance succeeds

    @bdd-task-markdown-export-task-export-skips-nested-git-directory @needs-review
    Example: Task Export Skips Nested Git Directory
      Given the pytest test setup is prepared
      When task export skips nested git directory is executed
      Then isinstance succeeds
      Then 'should not be exported' is not in content
      Then isinstance succeeds
      Then any succeeds

    @bdd-task-markdown-export-task-export-does-not-report-missing-plan-only-source-file @needs-review
    Example: Task Export Does Not Report Missing Plan Only Source File
      Given the pytest test setup is prepared
      When task export does not report missing plan only source file is executed
      Then isinstance succeeds
      Then all succeeds

    @bdd-task-markdown-export-task-export-does-not-report-git-scan-dot-as-source-file @needs-review
    Example: Task Export Does Not Report Git Scan Dot As Source File
      Given the pytest test setup is prepared
      When task export does not report git scan dot as source file is executed
      Then isinstance succeeds
      Then all succeeds

    @bdd-task-markdown-export-task-export-writes-markdown-file @needs-review
    Example: Task Export Writes Markdown File
      Given the pytest test setup is prepared
      When task export writes markdown file is executed
      Then exit_code equals 0
      Then 'wrote task export' is in stdout
      Then '# Compiled Task Export:' is in content
      Then '## Raw Taskledger Record Files' is in content

    @bdd-task-markdown-export-task-export-stdout-markdown @needs-review
    Example: Task Export Stdout Markdown
      Given the pytest test setup is prepared
      When task export stdout markdown is executed
      Then exit_code equals 0
      Then '# Compiled Task Export:' is in stdout
      Then '## Raw Taskledger Record Files' is in stdout

    @bdd-task-markdown-export-task-export-json-output-writes-file @needs-review
    Example: Task Export Json Output Writes File
      Given the pytest test setup is prepared
      When task export json output writes file is executed
      Then exit_code equals 0
      Then '# Compiled Task Export:' is in file_content

    @bdd-task-markdown-export-task-export-uses-active-task-default @needs-review
    Example: Task Export Uses Active Task Default
      Given the pytest test setup is prepared
      When task export uses active task default is executed
      Then exit_code equals 0

    @bdd-task-markdown-export-task-export-no-source-files-flag @needs-review
    Example: Task Export No Source Files Flag
      Given the pytest test setup is prepared
      When task export no source files flag is executed
      Then exit_code equals 0
      Then '## Source File Snapshots' is not in stdout

    @bdd-task-markdown-export-task-export-positional-task-ref @needs-review
    Example: Task Export Positional Task Ref
      Given the pytest test setup is prepared
      When task export positional task ref is executed
      Then exit_code equals 0
      Then 'wrote task export' is in stdout
