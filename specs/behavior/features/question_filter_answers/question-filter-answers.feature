@area-question_filter_answers @feature-question-filter-answers @generated @needs-review
Feature: Question Filter Answers

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-question-filter-answers
  Rule: Question Filter Answers

    @bdd-question-filter-answers-answers-markdown-format @needs-review
    Example: Answers Markdown Format
      Given the pytest test setup is prepared
      When answers markdown format is executed
      Then result.exit_code equals 0
      Then 'q-0001' is in result.output
      Then 'Q: Q1?' is in result.output
      Then 'A: A1' is in result.output

    @bdd-question-filter-answers-answers-empty-when-none-answered @needs-review
    Example: Answers Empty When None Answered
      Given the pytest test setup is prepared
      When answers empty when none answered is executed
      Then result.exit_code equals 0
      Then '(empty)' is in result.output

    @bdd-question-filter-answers-answer-empty-text-rejected @needs-review
    Example: Answer Empty Text Rejected
      Given the pytest test setup is prepared
      When answer empty text rejected is executed
      Then result.exit_code does not equal 0

    @bdd-question-filter-answers-answer-whitespace-only-rejected @needs-review
    Example: Answer Whitespace Only Rejected
      Given the pytest test setup is prepared
      When answer whitespace only rejected is executed
      Then result.exit_code does not equal 0
