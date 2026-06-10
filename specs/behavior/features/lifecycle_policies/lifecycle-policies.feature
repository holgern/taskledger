@area-lifecycle_policies @feature-lifecycle-policies @generated @needs-review
Feature: Lifecycle Policies

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-lifecycle-policies
  Rule: Lifecycle Policies

    @bdd-lifecycle-policies-plan-proposal-uses-durable-status-plus-active-planning @needs-review
    Example: Plan Proposal Uses Durable Status Plus Active Planning
      Given the pytest test setup is prepared
      When plan proposal uses durable status plus active planning is executed
      Then decision.ok is True

    @bdd-lifecycle-policies-implementation-mutation-allows-active-implementation-without-status-flip @needs-review
    Example: Implementation Mutation Allows Active Implementation Without Status Flip
      Given the pytest test setup is prepared
      When implementation mutation allows active implementation without status flip is executed
      Then decision.ok is True
