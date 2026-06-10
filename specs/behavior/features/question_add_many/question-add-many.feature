@area-question_add_many @feature-question-add-many @generated @needs-review
Feature: Question Add Many

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-question-add-many
  Rule: Question Add Many

    @bdd-question-add-many-question-add-many-adds-required-questions-to-active-task @needs-review
    Example: Question Add Many Adds Required Questions To Active Task
      Given the pytest test setup is prepared
      When question add many adds required questions to active task is executed
      Then result.exit_code equals 0
      Then isinstance succeeds

    @bdd-question-add-many-question-add-many-supports-yaml-file-and-explicit-task @needs-review
    Example: Question Add Many Supports Yaml File And Explicit Task
      Given the pytest test setup is prepared
      When question add many supports yaml file and explicit task is executed
      Then result.exit_code equals 0
      Then isinstance succeeds

    @bdd-question-add-many-question-add-many-rejects-blank-lines-without-partial-write @needs-review
    Example: Question Add Many Rejects Blank Lines Without Partial Write
      Given the pytest test setup is prepared
      When question add many rejects blank lines without partial write is executed
      Then result.exit_code does not equal 0
      Then listed.exit_code equals 0

    @bdd-question-add-many-question-add-many-rejects-duplicates-without-partial-write @needs-review
    Example: Question Add Many Rejects Duplicates Without Partial Write
      Given the pytest test setup is prepared
      When question add many rejects duplicates without partial write is executed
      Then result.exit_code does not equal 0
      Then listed.exit_code equals 0
