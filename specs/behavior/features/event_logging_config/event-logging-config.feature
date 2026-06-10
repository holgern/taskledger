@area-event_logging_config @feature-event-logging-config @generated @needs-review
Feature: Event Logging Config

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-event-logging-config
  Rule: Event Logging Config

    @bdd-event-logging-config-runtime-events-disabled-by-default @needs-review
    Example: Runtime Events Disabled By Default
      Given the pytest test setup is prepared
      When runtime events disabled by default is executed
      Then result.exit_code equals 0

    @bdd-event-logging-config-task-events-shows-empty-when-disabled @needs-review
    Example: Task Events Shows Empty When Disabled
      Given the pytest test setup is prepared
      When task events shows empty when disabled is executed
      Then result.exit_code equals 0

    @bdd-event-logging-config-lock-break-no-events-by-default @needs-review
    Example: Lock Break No Events By Default
      Given the pytest test setup is prepared
      When lock break no events by default is executed
      Then result.exit_code equals 0

    @bdd-event-logging-config-runtime-events-enabled-writes-events @needs-review
    Example: Runtime Events Enabled Writes Events
      Given the pytest test setup is prepared
      When runtime events enabled writes events is executed
      Then any succeeds

    @bdd-event-logging-config-lock-break-writes-events-when-enabled @needs-review
    Example: Lock Break Writes Events When Enabled
      Given the pytest test setup is prepared
      When lock break writes events when enabled is executed
      Then result.exit_code equals 0
      Then any succeeds

    @bdd-event-logging-config-existing-events-readable-after-disable @needs-review
    Example: Existing Events Readable After Disable
      Given the pytest test setup is prepared
      When existing events readable after disable is executed
      Then result.exit_code equals 0
