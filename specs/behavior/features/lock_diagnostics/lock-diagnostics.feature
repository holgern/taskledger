@area-lock_diagnostics @feature-lock-diagnostics @generated @needs-review
Feature: Lock Diagnostics

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-lock-diagnostics
  Rule: Lock Diagnostics

    @bdd-lock-diagnostics-diagnose-lock-none-returns-none-classification @needs-review
    Example: Diagnose Lock None Returns None Classification
      Given the pytest test setup is prepared
      When diagnose lock none returns none classification is executed
      Then diag.classification equals CLASSIFICATION_NONE
      Then diag.active is False
      Then diag.expired is False
      Then diag.holder is None

    @bdd-lock-diagnostics-diagnose-expired-impl-recommends-repair-flag @needs-review
    Example: Diagnose Expired Impl Recommends Repair Flag
      Given the pytest test setup is prepared
      When diagnose expired impl recommends repair flag is executed
      Then diag.classification equals CLASSIFICATION_EXPIRED
      Then diag.expired is True
      Then diag.active is True
      Then diag.seconds_until_expiry is not None
      Then diag.seconds_until_expiry is less than 0

    @bdd-lock-diagnostics-diagnose-lock-expired-planning-recommends-repair-lock @needs-review
    Example: Diagnose Lock Expired Planning Recommends Repair Lock
      Given the pytest test setup is prepared
      When diagnose lock expired planning recommends repair lock is executed
      Then diag.classification equals CLASSIFICATION_EXPIRED

    @bdd-lock-diagnostics-diagnose-lock-local-dead-pid-classifies-dead-local-process @needs-review
    Example: Diagnose Lock Local Dead Pid Classifies Dead Local Process
      Given the pytest test setup is prepared
      When diagnose lock local dead pid classifies dead local process is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_DEAD_LOCAL_PROCESS
      Then diag.holder_pid_check equals PID_CHECK_DEAD
      Then diag.expired is False
      Then diag.holder_pid equals 512425
      Then diag.holder_host equals HOST_LOCAL
      Then 'is no longer running' is in diag.summary
      Then any succeeds
      Then any succeeds
      Then any succeeds

    @bdd-lock-diagnostics-diagnose-lock-local-dead-pid-for-planning-only-recommends-repair @needs-review
    Example: Diagnose Lock Local Dead Pid For Planning Only Recommends Repair
      Given the pytest test setup is prepared
      When diagnose lock local dead pid for planning only recommends repair is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_DEAD_LOCAL_PROCESS
      Then all succeeds

    @bdd-lock-diagnostics-diagnose-lock-local-live-pid-other-actor-classifies-other-actor @needs-review
    Example: Diagnose Lock Local Live Pid Other Actor Classifies Other Actor
      Given the pytest test setup is prepared
      When diagnose lock local live pid other actor classifies other actor is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_OTHER_ACTOR
      Then diag.holder_pid_check equals PID_CHECK_ALIVE
      Then all succeeds

    @bdd-lock-diagnostics-diagnose-lock-local-live-pid-same-actor-classifies-same-actor @needs-review
    Example: Diagnose Lock Local Live Pid Same Actor Classifies Same Actor
      Given the pytest test setup is prepared
      When diagnose lock local live pid same actor classifies same actor is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_SAME_ACTOR
      Then diag.holder_pid_check equals PID_CHECK_ALIVE

    @bdd-lock-diagnostics-diagnose-lock-remote-host-is-unverifiable @needs-review
    Example: Diagnose Lock Remote Host Is Unverifiable
      Given the pytest test setup is prepared
      When diagnose lock remote host is unverifiable is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_UNVERIFIABLE_REMOTE_OR_UNKNOWN_PROCESS
      Then all succeeds
      Then any succeeds

    @bdd-lock-diagnostics-diagnose-lock-no-pid-local-host-classifies-no-pid @needs-review
    Example: Diagnose Lock No Pid Local Host Classifies No Pid
      Given the pytest test setup is prepared
      When diagnose lock no pid local host classifies no pid is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_NO_PID
      Then diag.holder_pid_check equals 'n/a'
      Then all succeeds

    @bdd-lock-diagnostics-diagnose-lock-same-actor-without-pid-still-classifies-same-actor @needs-review
    Example: Diagnose Lock Same Actor Without Pid Still Classifies Same Actor
      Given the pytest test setup is prepared
      When diagnose lock same actor without pid still classifies same actor is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_SAME_ACTOR

    @bdd-lock-diagnostics-diagnose-lock-unknown-pid-check-stays-unverifiable @needs-review
    Example: Diagnose Lock Unknown Pid Check Stays Unverifiable
      Given the pytest test setup is prepared
      When diagnose lock unknown pid check stays unverifiable is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_UNVERIFIABLE_REMOTE_OR_UNKNOWN_PROCESS
      Then diag.holder_pid_check equals PID_CHECK_UNKNOWN
      Then all succeeds

    @bdd-lock-diagnostics-diagnostics-to-dict-round-trips-through-payload-reconstruction @needs-review
    Example: Diagnostics To Dict Round Trips Through Payload Reconstruction
      Given the pytest test setup is prepared
      When diagnostics to dict round trips through payload reconstruction is executed
      Then rebuilt is not None
      Then rebuilt.classification equals CLASSIFICATION_ACTIVE_DEAD_LOCAL_PROCESS
      Then rebuilt.remediation equals diag.remediation
      Then rebuilt.summary equals diag.summary

    @bdd-lock-diagnostics-diagnose-lock-uses-task-id-in-remediation-when-provided @needs-review
    Example: Diagnose Lock Uses Task Id In Remediation When Provided
      Given the pytest test setup is prepared
      When diagnose lock uses task id in remediation when provided is executed
      Then all succeeds

    @bdd-lock-diagnostics-pi-harness-without-owner-pid-is-not-dead-local-process @needs-review
    Example: Pi Harness Without Owner Pid Is Not Dead Local Process
      Given the pytest test setup is prepared
      When pi harness without owner pid is not dead local process is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_HARNESS_SESSION
      Then all succeeds

    @bdd-lock-diagnostics-harness-owner-pid-dead-still-repairs @needs-review
    Example: Harness Owner Pid Dead Still Repairs
      Given the pytest test setup is prepared
      When harness owner pid dead still repairs is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_DEAD_LOCAL_PROCESS
      Then any succeeds

    @bdd-lock-diagnostics-legacy-pi-lock-with-session-inferred-as-unverifiable @needs-review
    Example: Legacy Pi Lock With Session Inferred As Unverifiable
      Given the pytest test setup is prepared
      When legacy pi lock with session inferred as unverifiable is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_HARNESS_SESSION
      Then all succeeds

    @bdd-lock-diagnostics-legacy-pi-lock-with-harness-ref-inferred-as-unverifiable @needs-review
    Example: Legacy Pi Lock With Harness Ref Inferred As Unverifiable
      Given the pytest test setup is prepared
      When legacy pi lock with harness ref inferred as unverifiable is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_HARNESS_SESSION
      Then all succeeds

    @bdd-lock-diagnostics-command-pid-scope-not-checkable @needs-review
    Example: Command Pid Scope Not Checkable
      Given the pytest test setup is prepared
      When command pid scope not checkable is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_HARNESS_SESSION
      Then all succeeds

    @bdd-lock-diagnostics-direct-user-dead-pid-still-repairs @needs-review
    Example: Direct User Dead Pid Still Repairs
      Given the pytest test setup is prepared
      When direct user dead pid still repairs is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_DEAD_LOCAL_PROCESS
      Then any succeeds

    @bdd-lock-diagnostics-harness-session-same-actor-classification @needs-review
    Example: Harness Session Same Actor Classification
      Given the pytest test setup is prepared
      When harness session same actor classification is executed
      Then diag.classification equals CLASSIFICATION_ACTIVE_SAME_ACTOR
