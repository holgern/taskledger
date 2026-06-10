@area-compact_mutation_output @feature-compact-mutation-output @generated @needs-review
Feature: Compact Mutation Output

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-compact-mutation-output
  Rule: Compact Mutation Output

    @bdd-compact-mutation-output-human-mode-does-not-contain-full-task @needs-review
    Example: Human Mode Does Not Contain Full Task
      Given the pytest test setup is prepared
      When human mode does not contain full task is executed
      Then result.exit_code equals 0
      Then '"task"' is not in result.stdout
      Then 'accepted_plan' is not in result.stdout

    @bdd-compact-mutation-output-json-mode-compact-payload @needs-review
    Example: Json Mode Compact Payload
      Given the pytest test setup is prepared
      When json mode compact payload is executed
      Then result.exit_code equals 0
      Then 'todo' is in result_data
      Then 'progress' is in result_data
      Then 'next_command' is in result_data
      Then 'accepted_plan' is not in result_data

    @bdd-compact-mutation-output-human-mode-does-not-contain-full-task-2 @needs-review
    Example: Human Mode Does Not Contain Full Task
      Given the pytest test setup is prepared
      When human mode does not contain full task is executed
      Then add_result.exit_code equals 0
      Then result.exit_code equals 0
      Then '"task"' is not in result.stdout
      Then 'accepted_plan' is not in result.stdout

    @bdd-compact-mutation-output-json-mode-compact-payload-2 @needs-review
    Example: Json Mode Compact Payload
      Given the pytest test setup is prepared
      When json mode compact payload is executed
      Then add_result.exit_code equals 0
      Then result.exit_code equals 0
      Then 'progress' is in result_data
      Then 'next_command' is in result_data
      Then 'accepted_plan' is not in result_data

    @bdd-compact-mutation-output-human-mode-does-not-contain-full-task-3 @needs-review
    Example: Human Mode Does Not Contain Full Task
      Given the pytest test setup is prepared
      When human mode does not contain full task is executed
      Then result.exit_code equals 0
      Then '"task"' is not in result.stdout
      Then 'accepted_plan' is not in result.stdout

    @bdd-compact-mutation-output-json-mode-compact-payload-3 @needs-review
    Example: Json Mode Compact Payload
      Given the pytest test setup is prepared
      When json mode compact payload is executed
      Then result.exit_code equals 0
      Then 'task_id' is in result_data
      Then 'run_id' is in result_data
      Then 'next_command' is in result_data
      Then 'accepted_plan' is not in result_data

    @bdd-compact-mutation-output-cli-implement-no-raw-render-json-payload @needs-review
    Example: Cli Implement No Raw Render Json Payload
      Given the pytest test setup is prepared
      When cli implement no raw render json payload is executed
      Then 'typer.echo(\n            render_json(' is not in content
