@area-question_plan_regeneration @feature-question-plan-regeneration @generated @needs-review
Feature: Question Plan Regeneration

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-question-plan-regeneration
  Rule: Question Plan Regeneration

    @bdd-question-plan-regeneration-required-question-blocks-approval-until-answered-and-regenerated @needs-review
    Example: Required Question Blocks Approval Until Answered And Regenerated
      Given the pytest test setup is prepared
      When required question blocks approval until answered and regenerated is executed
      Then blocked.exit_code does not equal 0

    @bdd-question-plan-regeneration-plan-regeneration-finishes-orphaned-latest-planning-run @needs-review
    Example: Plan Regeneration Finishes Orphaned Latest Planning Run
      Given the pytest test setup is prepared
      When plan regeneration finishes orphaned latest planning run is executed
      Then task.latest_planning_run is not None
      Then regenerated.exit_code equals 0
      Then run.status equals 'finished'

    @bdd-question-plan-regeneration-answered-question-blocks-approval-of-stale-plan @needs-review
    Example: Answered Question Blocks Approval Of Stale Plan
      Given the pytest test setup is prepared
      When answered question blocks approval of stale plan is executed
      Then blocked.exit_code equals 3

    @bdd-question-plan-regeneration-answer-many-rejects-duplicate-plain-text-ids @needs-review
    Example: Answer Many Rejects Duplicate Plain Text Ids
      Given the pytest test setup is prepared
      When answer many rejects duplicate plain text ids is executed
      Then result.exit_code does not equal 0

    @bdd-question-plan-regeneration-required-question-needs-explicit-user-source-for-agent @needs-review
    Example: Required Question Needs Explicit User Source For Agent
      Given the pytest test setup is prepared
      When required question needs explicit user source for agent is executed
      Then result.exit_code does not equal 0

    @bdd-question-plan-regeneration-question-answer-accepts-question-option-alias @needs-review
    Example: Question Answer Accepts Question Option Alias
      Given the pytest test setup is prepared
      When question answer accepts question option alias is executed
      Then result.exit_code equals 0

    @bdd-question-plan-regeneration-question-answer-rejects-both-positional-and-option-id @needs-review
    Example: Question Answer Rejects Both Positional And Option Id
      Given the pytest test setup is prepared
      When question answer rejects both positional and option id is executed
      Then result.exit_code does not equal 0
      Then 'Provide exactly one question id' is in combined

    @bdd-question-plan-regeneration-question-status-human-lists-required-open-ids @needs-review
    Example: Question Status Human Lists Required Open Ids
      Given the pytest test setup is prepared
      When question status human lists required open ids is executed
      Then result.exit_code equals 0
      Then 'Open required questions: q-0002' is in result.stdout
      Then 'Answered required questions: q-0001' is in result.stdout
      Then 'Do not infer answers.' is in result.stdout

    @bdd-question-plan-regeneration-plan-upsert-from-answers-releases-planning-lock-and-allows-accept @needs-review
    Example: Plan Upsert From Answers Releases Planning Lock And Allows Accept
      Given the pytest test setup is prepared
      When plan upsert from answers releases planning lock and allows accept is executed
      Then accepted.exit_code equals 0
