@area-agent_command_logging @feature-agent-command-logging @generated @needs-review
Feature: Agent Command Logging

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-agent-command-logging
  Rule: Agent Command Logging

    @bdd-agent-command-logging-agent-logging-config-validation-and-defaults @needs-review
    Example: Agent Logging Config Validation And Defaults
      Given the pytest test setup is prepared
      When agent logging config validation and defaults is executed
      Then config.agent_logging.enabled is False

    @bdd-agent-command-logging-cli-success-command-is-captured-when-enabled @needs-review
    Example: Cli Success Command Is Captured When Enabled
      Given the pytest test setup is prepared
      When cli success command is captured when enabled is executed
      Then result.exit_code equals 0
      Then cli_logs is truthy
      Then record.status equals 'succeeded'
      Then record.exit_code equals 0
      Then record.operation_name equals 'task.create'
      Then record.task_id equals 'task-0001'
      Then record.visible_stdout_excerpt is not None
      Then 'created task' is in record.visible_stdout_excerpt

    @bdd-agent-command-logging-cli-error-command-is-captured-when-enabled @needs-review
    Example: Cli Error Command Is Captured When Enabled
      Given the pytest test setup is prepared
      When cli error command is captured when enabled is executed
      Then result.exit_code does not equal 0
      Then failures is truthy
      Then record.exit_code is not None
      Then record.error_code is not None
      Then record.error_summary is not None
      Then 'Task not found' is in record.error_summary

    @bdd-agent-command-logging-managed-shell-capture-and-transcript-report-rendering @needs-review
    Example: Managed Shell Capture And Transcript Report Rendering
      Given the pytest test setup is prepared
      When managed shell capture and transcript report rendering is executed
      Then result.exit_code equals 0
      Then managed_logs is truthy
      Then managed.run_id is not None
      Then managed.run_type equals 'implementation'
      Then managed.managed_command_exit_code equals 0
      Then managed.managed_stdout_ref is not None
      Then managed.managed_stderr_ref is not None
      Then transcript.exit_code equals 0
      Then '## Raw Command Transcript' is in transcript.stdout
      Then report.exit_code equals 0
      Then '## Command Transcript' is in report.stdout
      Then '| Time | Exit | Command | Result |' is in report.stdout

    @bdd-agent-command-logging-task-transcript-json-contract @needs-review
    Example: Task Transcript Json Contract
      Given the pytest test setup is prepared
      When task transcript json contract is executed
      Then result.exit_code equals 0

    @bdd-agent-command-logging-task-transcript-review-mode-groups-wrapper-and-managed-shell @needs-review
    Example: Task Transcript Review Mode Groups Wrapper And Managed Shell
      Given the pytest test setup is prepared
      When task transcript review mode groups wrapper and managed shell is executed
      Then transcript.exit_code equals 0
      Then '## Transcript Review' is in transcript.stdout
      Then 'failed, wrapper mismatch' is in transcript.stdout

    @bdd-agent-command-logging-task-transcript-failures-mode-renders-failed-rows-only @needs-review
    Example: Task Transcript Failures Mode Renders Failed Rows Only
      Given the pytest test setup is prepared
      When task transcript failures mode renders failed rows only is executed
      Then failing.exit_code equals 0
      Then failures.exit_code equals 0
      Then '## Transcript Failures' is in failures.stdout
      Then 'raise SystemExit(3)' is in failures.stdout
      Then '| - | 3 |' is in failures.stdout

    @bdd-agent-command-logging-transcript-tolerates-duplicate-log-ids-by-default @needs-review
    Example: Transcript Tolerates Duplicate Log Ids By Default
      Given the pytest test setup is prepared
      When transcript tolerates duplicate log ids by default is executed
      Then transcript.exit_code equals 0
      Then '## Transcript Review' is in transcript.stdout
      Then '### Duplicate Log IDs' is in transcript.stdout
      Then '- dup-0001' is in transcript.stdout

    @bdd-agent-command-logging-default-transcript-produces-review-output @needs-review
    Example: Default Transcript Produces Review Output
      Given the pytest test setup is prepared
      When default transcript produces review output is executed
      Then transcript.exit_code equals 0
      Then '## Transcript Review' is in transcript.stdout
      Then '### Summary' is in transcript.stdout

    @bdd-agent-command-logging-raw-flag-produces-raw-table-output @needs-review
    Example: Raw Flag Produces Raw Table Output
      Given the pytest test setup is prepared
      When raw flag produces raw table output is executed
      Then transcript.exit_code equals 0
      Then '## Raw Command Transcript' is in transcript.stdout
      Then '## Transcript Review' is not in transcript.stdout

    @bdd-agent-command-logging-report-command-log-uses-logical-rows @needs-review
    Example: Report Command Log Uses Logical Rows
      Given the pytest test setup is prepared
      When report command log uses logical rows is executed
      Then report.exit_code equals 0
      Then '| Time | Exit | Command | Result |' is in report.stdout
      Then 'python -c' is in report.stdout
      Then '| Time | Exit | Kind | Command | Output |' is not in report.stdout

    @bdd-agent-command-logging-duplicate-log-id-warning-in-raw-mode @needs-review
    Example: Duplicate Log Id Warning In Raw Mode
      Given the pytest test setup is prepared
      When duplicate log id warning in raw mode is executed
      Then transcript.exit_code equals 0
      Then '## Raw Command Transcript' is in transcript.stdout
      Then '### Duplicate Log IDs' is in transcript.stdout
      Then '- dup-raw-001' is in transcript.stdout
