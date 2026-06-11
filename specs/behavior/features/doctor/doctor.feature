@area-doctor @feature-doctor @generated @needs-review
Feature: Doctor

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-doctor
  Rule: Doctor

    @bdd-doctor-inspect-project-reports-malformed-handoff-record @needs-review
    Example: Inspect Project Reports Malformed Handoff Record
      Given the pytest test setup is prepared
      When inspect project reports malformed handoff record is executed
      Then any succeeds

    @bdd-doctor-inspect-project-warns-for-unsupported-legacy-sidecar @needs-review
    Example: Inspect Project Warns For Unsupported Legacy Sidecar
      Given the pytest test setup is prepared
      When inspect project warns for unsupported legacy sidecar is executed
      Then any succeeds
      Then any succeeds

    @bdd-doctor-inspect-project-active-task-missing @needs-review
    Example: Inspect Project Active Task Missing
      Given the pytest test setup is prepared
      When inspect project active task missing is executed
      Then any succeeds

    @bdd-doctor-inspect-project-active-task-done-warns @needs-review
    Example: Inspect Project Active Task Done Warns
      Given the pytest test setup is prepared
      When inspect project active task done warns is executed
      Then any succeeds

    @bdd-doctor-inspect-broken-introduction-ref @needs-review
    Example: Inspect Broken Introduction Ref
      Given the pytest test setup is prepared
      When inspect broken introduction ref is executed
      Then any succeeds

    @bdd-doctor-inspect-broken-requirement-ref @needs-review
    Example: Inspect Broken Requirement Ref
      Given the pytest test setup is prepared
      When inspect broken requirement ref is executed
      Then any succeeds

    @bdd-doctor-inspect-accepted-plan-version-missing @needs-review
    Example: Inspect Accepted Plan Version Missing
      Given the pytest test setup is prepared
      When inspect accepted plan version missing is executed
      Then any succeeds

    @bdd-doctor-inspect-multiple-accepted-plans @needs-review
    Example: Inspect Multiple Accepted Plans
      Given the pytest test setup is prepared
      When inspect multiple accepted plans is executed
      Then any succeeds

    @bdd-doctor-inspect-accepted-plan-version-points-to-wrong-plan @needs-review
    Example: Inspect Accepted Plan Version Points To Wrong Plan
      Given the pytest test setup is prepared
      When inspect accepted plan version points to wrong plan is executed
      Then any succeeds

    @bdd-doctor-doctor-warns-for-worker-refs-without-enabled-pipeline @needs-review
    Example: Doctor Warns For Worker Refs Without Enabled Pipeline
      Given the pytest test setup is prepared
      When doctor warns for worker refs without enabled pipeline is executed
      Then any succeeds
      Then any succeeds

    @bdd-doctor-doctor-warns-for-worker-refs-missing-from-pipeline @needs-review
    Example: Doctor Warns For Worker Refs Missing From Pipeline
      Given the pytest test setup is prepared
      When doctor warns for worker refs missing from pipeline is executed
      Then any succeeds
      Then any succeeds

    @bdd-doctor-inspect-transient-stage-in-status @needs-review
    Example: Inspect Transient Stage In Status
      Given the pytest test setup is prepared
      When inspect transient stage in status is executed
      Then any succeeds

    @bdd-doctor-inspect-multiple-running-runs @needs-review
    Example: Inspect Multiple Running Runs
      Given the pytest test setup is prepared
      When inspect multiple running runs is executed
      Then any succeeds

    @bdd-doctor-inspect-running-run-without-matching-lock @needs-review
    Example: Inspect Running Run Without Matching Lock
      Given the pytest test setup is prepared
      When inspect running run without matching lock is executed
      Then any succeeds

    @bdd-doctor-doctor-reports-missing-lock-for-running-implementation-with-recovery-hint @needs-review
    Example: Doctor Reports Missing Lock For Running Implementation With Recovery Hint
      Given the pytest test setup is prepared
      When doctor reports missing lock for running implementation with recovery hint is executed
      Then any succeeds
      Then any succeeds

    @bdd-doctor-inspect-lock-without-running-run @needs-review
    Example: Inspect Lock Without Running Run
      Given the pytest test setup is prepared
      When inspect lock without running run is executed
      Then any succeeds

    @bdd-doctor-inspect-change-references-missing-run @needs-review
    Example: Inspect Change References Missing Run
      Given the pytest test setup is prepared
      When inspect change references missing run is executed
      Then any succeeds

    @bdd-doctor-inspect-change-references-non-implementation-run @needs-review
    Example: Inspect Change References Non Implementation Run
      Given the pytest test setup is prepared
      When inspect change references non implementation run is executed
      Then any succeeds

    @bdd-doctor-inspect-validation-run-references-missing-impl @needs-review
    Example: Inspect Validation Run References Missing Impl
      Given the pytest test setup is prepared
      When inspect validation run references missing impl is executed
      Then any succeeds

    @bdd-doctor-inspect-validation-run-references-non-impl-run @needs-review
    Example: Inspect Validation Run References Non Impl Run
      Given the pytest test setup is prepared
      When inspect validation run references non impl run is executed
      Then any succeeds

    @bdd-doctor-inspect-lock-references-missing-task @needs-review
    Example: Inspect Lock References Missing Task
      Given the pytest test setup is prepared
      When inspect lock references missing task is executed
      Then any succeeds

    @bdd-doctor-inspect-lock-references-non-running-run @needs-review
    Example: Inspect Lock References Non Running Run
      Given the pytest test setup is prepared
      When inspect lock references non running run is executed
      Then any succeeds

    @bdd-doctor-inspect-lock-stage-run-type-mismatch @needs-review
    Example: Inspect Lock Stage Run Type Mismatch
      Given the pytest test setup is prepared
      When inspect lock stage run type mismatch is executed
      Then any succeeds

    @bdd-doctor-inspect-expired-lock @needs-review
    Example: Inspect Expired Lock
      Given the pytest test setup is prepared
      When inspect expired lock is executed
      Then any succeeds

    @bdd-doctor-inspect-lock-references-missing-run @needs-review
    Example: Inspect Lock References Missing Run
      Given the pytest test setup is prepared
      When inspect lock references missing run is executed
      Then any succeeds

    @bdd-doctor-doctor-warns-about-empty-orphan-slug-dir @needs-review
    Example: Doctor Warns About Empty Orphan Slug Dir
      Given the pytest test setup is prepared
      When doctor warns about empty orphan slug dir is executed
      Then any succeeds
      Then any succeeds

    @bdd-doctor-doctor-warns-about-non-empty-legacy-sidecar @needs-review
    Example: Doctor Warns About Non Empty Legacy Sidecar
      Given the pytest test setup is prepared
      When doctor warns about non empty legacy sidecar is executed
      Then any succeeds

    @bdd-doctor-healthy-project-has-no-findings
    Example: A healthy project has no integrity findings
      Given an initialized project has consistent canonical state
      When Taskledger doctor inspects the project
      Then the project is reported healthy

    @bdd-doctor-duplicate-todo-ids-are-reported
    Example: Duplicate todo IDs are reported
      Given a task contains duplicate todo identifiers
      When Taskledger doctor inspects the project
      Then the duplicate identifiers are reported as integrity errors

    @bdd-doctor-run-lock-mismatch-is-reported
    Example: Run and lock mismatches are reported
      Given an active run and lock identify different lifecycle operations
      When Taskledger doctor inspects locks
      Then the mismatch is reported with recovery guidance
