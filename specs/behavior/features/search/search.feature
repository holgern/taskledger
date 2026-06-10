@area-search @feature-search @generated @needs-review
Feature: Search

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-search
  Rule: Search

    @bdd-search-search-grep-and-symbols-basic @needs-review
    Example: Search Grep And Symbols Basic
      Given the pytest test setup is prepared
      When search grep and symbols basic is executed
      Then any succeeds
      Then any succeeds
      Then any succeeds
      Then 'file1.py' is in seen
      Then 'file2.txt' is in seen
      Then all succeeds

    @bdd-search-module-dependencies-and-errors @needs-review
    Example: Module Dependencies And Errors
      Given the pytest test setup is prepared
      When module dependencies and errors is executed
      Then info.repo equals 'repo_b'
      Then info.module equals 'mymodule'
      Then '__manifest__.py' is in info.manifest_path

    @bdd-search-discovery-tokens-and-discover-files @needs-review
    Example: Discovery Tokens And Discover Files
      Given the pytest test setup is prepared
      When discovery tokens and discover files is executed
      Then all succeeds
      Then any succeeds
