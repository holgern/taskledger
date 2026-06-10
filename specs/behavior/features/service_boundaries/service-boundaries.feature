@area-service_boundaries @feature-service-boundaries @generated @needs-review
Feature: Service Boundaries

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-service-boundaries
  Rule: Service Boundaries

    @bdd-service-boundaries-boundary-whitelists-include-reasons @needs-review
    Example: Boundary Whitelists Include Reasons
      Given the pytest test setup is prepared
      When boundary whitelists include reasons is executed
      Then key is truthy
      Then reason.strip succeeds

    @bdd-service-boundaries-service-module-line-budget @needs-review
    Example: Service Module Line Budget
      Given the pytest test setup is prepared
      When service module line budget is executed
      Then unexpected is falsy
      Then stale is falsy

    @bdd-service-boundaries-service-function-line-budget @needs-review
    Example: Service Function Line Budget
      Given the pytest test setup is prepared
      When service function line budget is executed
      Then unexpected is falsy
      Then stale is falsy

    @bdd-service-boundaries-except-exception-sites-are-whitelisted @needs-review
    Example: Except Exception Sites Are Whitelisted
      Given the pytest test setup is prepared
      When except exception sites are whitelisted is executed
      Then unexpected is falsy
      Then stale is falsy

    @bdd-service-boundaries-cli-services-imports-are-whitelisted @needs-review
    Example: Cli Services Imports Are Whitelisted
      Given the pytest test setup is prepared
      When cli services imports are whitelisted is executed
      Then unexpected is falsy
      Then stale is falsy

    @bdd-service-boundaries-validation-module-has-no-private-tasks-imports @needs-review
    Example: Validation Module Has No Private Tasks Imports
      Given the pytest test setup is prepared
      When validation module has no private tasks imports is executed
      Then forbidden is falsy

    @bdd-service-boundaries-tasks-validation-gate-wrapper-has-no-local-import-workaround @needs-review
    Example: Tasks Validation Gate Wrapper Has No Local Import Workaround
      Given the pytest test setup is prepared
      When tasks validation gate wrapper has no local import workaround is executed
      Then target is not None
      Then local_imports is falsy
