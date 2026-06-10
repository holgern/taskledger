@area-find_code_clones_script @feature-find-code-clones-script @generated @needs-review
Feature: Find Code Clones Script

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-find-code-clones-script
  Rule: Find Code Clones Script

    @bdd-find-code-clones-script-find-code-clones-script-json-and-include-tests @needs-review
    Example: Find Code Clones Script Json And Include Tests
      Given the pytest test setup is prepared
      When find code clones script json and include tests is executed
      Then 'scan: files=' is in human.stdout
