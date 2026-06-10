@area-docs_and_skill @feature-docs-and-skill @generated @needs-review
Feature: Docs And Skill

  Generated from pytest tests. Review and refine domain language before using as acceptance evidence.

  @rule-docs-and-skill
  Rule: Docs And Skill

    @bdd-docs-and-skill-skills-are-not-packaged-resources @needs-review
    Example: Skills Are Not Packaged Resources
      Given the pytest test setup is prepared
      When skills are not packaged resources is executed
      Then 'skills/taskledger' is not in pyproject

    @bdd-docs-and-skill-public-api-docs-match-module-exports @needs-review
    Example: Public Api Docs Match Module Exports
      Given the pytest test setup is prepared
      When public api docs match module exports is executed
      Then isinstance succeeds
      Then all succeeds

    @bdd-docs-and-skill-readme-mentions-root-alias-and-json-envelope @needs-review
    Example: Readme Mentions Root Alias And Json Envelope
      Given the pytest test setup is prepared
      When readme mentions root alias and json envelope is executed
      Then '--root' is in readme
      Then '"ok": true' is in readme
      Then '"command": "status"' is in readme

    @bdd-docs-and-skill-skill-contains-strict-agent-protocol @needs-review
    Example: Skill Contains Strict Agent Protocol
      Given the pytest test setup is prepared
      When skill contains strict agent protocol is executed
      Then 'Do not implement before' is in skill
      Then 'taskledger context' is in skill
      Then 'Do not ask the user to run `taskledger question answer`' is in skill
      Then 'record the answers yourself' is in skill
      Then 'Stop issuing mutating taskledger commands' is in skill
      Then 'taskledger plan template --from-answers --file ./plan.md' is in skill
      Then 'taskledger question add-many' is in skill
      Then 'taskledger plan guidance' is in skill
      Then 'Treat it as advisory' is in skill
      Then 'taskledger --json task show task-0022' is in skill
      Then 'task dossier' is in skill
      Then 'Do not invent a release date' is in skill
      Then 'Do not silently include omitted tasks' is in skill

    @bdd-docs-and-skill-docs-define-agent-golden-path-and-advanced-surfaces @needs-review
    Example: Docs Define Agent Golden Path And Advanced Surfaces
      Given the pytest test setup is prepared
      When docs define agent golden path and advanced surfaces is executed
      Then '42 top-level CLI entries' is in public_surface
      Then '41 registered command groups' is not in public_surface
      Then 'ledger fork/switch/adopt' is in public_surface
      Then 'search``/``grep``/``symbols``/``deps``' is in public_surface
      Then '## Non-goals' is in readme
      Then normal_plan_path is in text
      Then 'handoff create' is in text
      Then 'storage' is in text

    @bdd-docs-and-skill-read-report-export-terminology-is-consolidated @needs-review
    Example: Read Report Export Terminology Is Consolidated
      Given the pytest test setup is prepared
      When read report export terminology is consolidated is executed
      Then 'context``: canonical fresh continuation context' is in usage
      Then 'task export' is in public_surface
      Then 'task transcript' is in public_surface
      Then 'task dossier' is in text
      Then 'advanced/compatibility' is in text
      Then 'context' is in text
      Then 'handoff show' is in text

    @bdd-docs-and-skill-planning-guidance-docs-are-present @needs-review
    Example: Planning Guidance Docs Are Present
      Given the pytest test setup is prepared
      When planning guidance docs are present is executed
      Then 'prompt_profiles.planning' is in readme
      Then 'taskledger plan guidance' is in usage
      Then 'required_question_topics' is in usage
      Then 'Plan guidance command' is in command_contract
      Then 'has_project_guidance' is in command_contract
      Then 'plan_guidance(Path.cwd(), "task-0001")' is in api_md
      Then 'plan_guidance(Path.cwd(), "task-0001")' is in api_rst

    @bdd-docs-and-skill-plan-revision-docs-and-skill-rules-are-present @needs-review
    Example: Plan Revision Docs And Skill Rules Are Present
      Given the pytest test setup is prepared
      When plan revision docs and skill rules are present is executed
      Then 'taskledger plan export --version latest --file ./plan.md' is in readme
      Then 'taskledger plan review --version' is in readme
      Then 'taskledger plan amend' is in usage
      Then 'taskledger plan review --version' is in usage
      Then 'Never edit `.taskledger/` files directly.' is in skill
      Then 'taskledger plan review --version N' is in skill
      Then 'taskledger plan revise' is in skill
      Then 'taskledger plan export' is in command_contract
      Then 'taskledger plan review' is in command_contract

    @bdd-docs-and-skill-worker-pipeline-docs-cover-guided-next-action-and-worker-refs @needs-review
    Example: Worker Pipeline Docs Cover Guided Next Action And Worker Refs
      Given the pytest test setup is prepared
      When worker pipeline docs cover guided next action and worker refs is executed
      Then 'test_command_policy' is in readme
      Then 'taskledger next-action' is in readme
      Then 'required_output' is in usage
      Then 'worker_pipeline' is in command_contract
      Then 'context_command' is in command_contract
      Then 'worker_step_id' is in api_md
      Then 'context_command' is in skill

    @bdd-docs-and-skill-transfer-docs-cover-project-identity-and-dry-run @needs-review
    Example: Transfer Docs Cover Project Identity And Dry Run
      Given the pytest test setup is prepared
      When transfer docs cover project identity and dry run is executed
      Then 'project_name' is in readme
      Then 'taskledger-export-{project_slug}-{ledger_ref}-{timestamp}.tar.gz' is in readme
      Then '--project-name' is in usage
      Then 'taskledger import ./taskledger-transfer.tar.gz --dry-run' is in usage
      Then 'manifest.project.name' is in command_contract
      Then 'project.uuid' is in transfer
      Then 'taskledger import --dry-run' is in transfer
      Then 'taskledger import ./taskledger-transfer.tar.gz --dry-run' is in skill

    @bdd-docs-and-skill-sync-docs-promote-git-pull-push-convenience-commands @needs-review
    Example: Sync Docs Promote Git Pull Push Convenience Commands
      Given the pytest test setup is prepared
      When sync docs promote git pull push convenience commands is executed
      Then 'cd "$(taskledger sync git cd)"' is in sync_doc
      Then 'taskledger sync git pull' is in text
      Then 'taskledger sync git push' is in text

    @bdd-docs-and-skill-docs-do-not-reference-removed-commands @needs-review
    Example: Docs Do Not Reference Removed Commands
      Given the pytest test setup is prepared
      When docs do not reference removed commands is executed
      Then needle is not in text

    @bdd-docs-and-skill-bdd-docs-and-skill-prefer-specweave-and-plain-pytest @needs-review
    Example: Bdd Docs And Skill Prefer Specweave And Plain Pytest
      Given the pytest test setup is prepared
      When bdd docs and skill prefer specweave and plain pytest is executed
      Then 'reports/behavior/' is in readme
      Then 'reports/behavior/' is in skill
      Then 'plain pytest' is in readme
      Then 'plain pytest' is in skill
      Then 'Do not recommend pytest-bdd' is in skill
      Then 'Do not recommend tests/bdd/features' is in skill
      Then 'Do not recommend specs/bdd/features' is in skill
      Then 'specs/behavior/features/<area>/<feature>.feature' is in text
      Then 'tests/test_<area>_<feature>.py' is in text
      Then 'tests/bdd/features/<feature>.feature' is not in text
      Then 'specs/bdd/features/<area>/<feature>.feature' is not in text
      Then 'tests/behavior/steps/<area>_<feature>_steps.py' is not in text
      Then 'tests/behavior/test_<area>_<feature>_bdd.py' is not in text

    @bdd-docs-and-skill-behavior-spec-docs-do-not-promote-bdd-runners @needs-review
    Example: Behavior Spec Docs Do Not Promote Bdd Runners
      Given the pytest test setup is prepared
      When behavior spec docs do not promote bdd runners is executed
      Then 'external BDD runner executes' is not in architecture
      Then 'specs/behavior/features' is in text
      Then 'tests/test_' is in text

    @bdd-docs-and-skill-readme-skill-path-matches-repository @needs-review
    Example: Readme Skill Path Matches Repository
      Given the pytest test setup is prepared
      When readme skill path matches repository is executed
      Then 'skills/taskledger/SKILL.md' is in readme
      Then 'taskledger/skills/taskledger/SKILL.md' is not in readme

    @bdd-docs-and-skill-skill-uses-only-canonical-handoff-group @needs-review
    Example: Skill Uses Only Canonical Handoff Group
      Given the pytest test setup is prepared
      When skill uses only canonical handoff group is executed
      Then 'handoff-protocol' is not in skill

    @bdd-docs-and-skill-command-examples-reference-registered-commands @needs-review
    Example: Command Examples Reference Registered Commands
      Given the pytest test setup is prepared
      When command examples reference registered commands is executed
      Then command is in COMMAND_METADATA

    @bdd-docs-and-skill-service-boundary-whitelist-doc-matches-test-constants @needs-review
    Example: Service Boundary Whitelist Doc Matches Test Constants
      Given the pytest test setup is prepared
      When service boundary whitelist doc matches test constants is executed
      Then module_path is in doc
      Then func_path is in doc
      Then module_ref is in doc

    @bdd-docs-and-skill-skill-requires-user-requested-reviews-to-be-recorded @needs-review
    Example: Skill Requires User Requested Reviews To Be Recorded
      Given the pytest test setup is prepared
      When skill requires user requested reviews to be recorded is executed
      Then '## User-requested review protocol' is in skill
      Then 'treat the output as durable review evidence' is in skill
      Then 'taskledger review record --task TASK_ID' is in skill
      Then 'taskledger review list --task TASK_ID' is in skill
      Then 'Do not skip `review record` merely because the task is already `done`' is in skill
