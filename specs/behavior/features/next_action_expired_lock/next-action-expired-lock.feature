@area-next_action_expired_lock @feature-next-action-expired-lock @generated @needs-review
Feature: Next Action Expired Lock

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-next-action-expired-lock
  Rule: Next Action Expired Lock

    @bdd-next-action-expired-lock-expired-impl-lock-next-action-recommends-resume @needs-review
    Example: Expired Impl Lock Next Action Recommends Resume
      Given the pytest test setup is prepared
      When expired impl lock next action recommends resume is executed
      Then r.exit_code equals 0

    @bdd-next-action-expired-lock-expired-impl-lock-resume-succeeds @needs-review
    Example: Expired Impl Lock Resume Succeeds
      Given the pytest test setup is prepared
      When expired impl lock resume succeeds is executed
      Then r.exit_code equals 0

    @bdd-next-action-expired-lock-expired-planning-lock-still-routes-to-repair @needs-review
    Example: Expired Planning Lock Still Routes To Repair
      Given the pytest test setup is prepared
      When expired planning lock still routes to repair is executed
      Then r.exit_code equals 0
      Then r.exit_code equals 0
      Then r.exit_code equals 0
      Then r.exit_code equals 0
