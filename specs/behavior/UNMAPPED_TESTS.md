# Intentionally Unmapped Pytest Coverage

SpecWeave behavior coverage maps tests that enforce observable product behavior.
Low-level implementation tests remain intentionally unmapped when they only verify
internal parsing, serialization helpers, command classification, or utility edge
cases already covered by a mapped behavior at a higher layer.

Current intentional exclusions include:

- `tests/test_storage_common.py`: JSON/text I/O helpers, path conversion,
  summarization boundaries, hashing, and empty merge cases.
- `tests/test_implementation_checks.py`: model rejection paths and command-category
  classification for individual tool spellings.
- `tests/test_no_log_feature.py`: command-name extraction mechanics, false
  environment values, and positive branches of internal skip predicates.
- `tests/test_project_root_config.py`: repeated invalid-value variants after one
  representative behavior mapping per public configuration rule.
- `tests/test_command_inventory.py`: enum-domain checks, inventory budgets, and
  repeated metadata assertions already represented by broader inventory contracts.
- `tests/test_bdd_models.py`: repeated model type rejection and status-normalizer
  variants after defaults and round-trip serialization are behavior-mapped.
- `tests/test_doctor.py`: healthy helper sub-checks and count/reporting details
  already represented by project-level doctor integrity behavior.
- `tests/test_domain_policies.py`: equivalent branches of active-stage derivation,
  planning permission, metadata editing, and known-role validation.
- `tests/test_bdd_report_import.py`: equivalent malformed-format cases and parser
  container variants after representative import outcomes are mapped.
- `tests/test_ready_work.py`: priority parsing and exhaustive command-table checks
  supporting the mapped ready-work selection contract.
- `tests/test_monitor.py`: text heading and focused-row rendering details after
  snapshot grouping and activity scopes are behavior-mapped.
- `tests/test_bdd_storage.py`: equivalent collection round trips, empty loads, and
  not-found cases after one representative mapping for each storage contract.
- `tests/test_storage_repos.py`: repeated invalid repository kind/role/path variants
  after representative repository validation and resolution behavior is mapped.
- `tests/test_handoff_lifecycle.py`: summary rendering and empty-list convenience
  cases after creation, listing, modes, metadata, and transition guards are mapped.
- `tests/test_actor_harness_state.py`: idempotent missing-state clears and model
  type-rejection variants after persistence, absence, and precedence are mapped.
- `tests/test_workflow_guidance.py`: private label-formatting helpers and the
  no-config predicate after complete rendered-guidance behavior is mapped.
- `tests/test_taskledger_v2_exchange.py`: explicit-path grammar and equivalent
  archive size-limit variants after import safety and preservation are mapped.
- `tests/test_doctor.py`: component-level healthy checks, report counts, and
  canonical-directory no-warning cases after project integrity behavior is mapped.
- `tests/test_worker_pipeline_config.py`: equivalent invalid field, enum, duplicate,
  and unknown-key variants after representative configuration rejection is mapped.
- `tests/test_services_dashboard.py`: equivalent active/explicit task selection and
  individual resource-count variants after dashboard aggregation is mapped.
- `tests/test_question_filter_answers.py`: equivalent answered, dismissed,
  comma-separated, and empty-result status filters after filtering is mapped.
- `tests/test_docs_and_skill.py`: repository layout, link, RST-only, and exact
  whitelist consistency checks supporting broader documentation contracts.
- `tests/test_tree_command.py`: JSON envelope, scope echo, active marker, and null
  detail-shape checks after tree hierarchy and JSON behavior are already mapped.
- `tests/test_release_changelog.py`: project-name presentation after release
  selection, persistence, omission, and markdown evidence behavior is mapped.
- `tests/test_question_plan_regeneration.py`: repeated text option parsing after
  answer-many persistence and stale-plan regeneration behavior is mapped.
- `tests/test_bdd_gherkin.py`: missing acceptance-link warning after export
  preconditions, workspace safety, tags, and deterministic output are mapped.

These tests remain part of the normal pytest suite. They should gain behavior
scenarios only when the behavior is independently observable or becomes a public
contract.
