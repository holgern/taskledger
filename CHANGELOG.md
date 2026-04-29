# Changelog

## v0.1.1 - 2026-04-29

### Added

- Added `task follow-up` to create linked post-completion child tasks, preserve closure metadata, and show parent and follow-up relationships in task and handoff views.
- Added durable release records and a new `taskledger release` command group with `tag`, `list`, `show`, and `changelog`, including export/import support and public API coverage.
- Added planning helpers with `question add-many`, `plan template`, richer regeneration hints in `next-action`, and recovery commands for orphaned implementation work with `implement resume`, `task uncancel`, and `can implement-resume`.

### Changed

- Hardened CLI startup so optional command-group import failures no longer block core commands, and launcher failures return structured diagnostics.

### Fixed

- Fixed recovery guidance for uncancelled tasks with orphaned implementation runs so `next-action` and `can implement` recommend `implement resume` instead of a fresh start.

### Documentation

- Documented release tagging, changelog generation, planning helpers, follow-up task workflow, and recovery semantics across README, RST docs, API docs, and the taskledger skill.

### Quality

- Expanded regression coverage for follow-up tasks, release workflow, CLI import resilience, planning helpers, and implementation recovery. Repo-wide pytest, ruff, and mypy passed.

## v0.1.0 - 2026-04-29

### Added

- Added initial unit test coverage for `storage/common`, `storage/init`, `storage/repos`, `domain/policies`, and `services/doctor_v2`, raising overall coverage from 62% to 65%.
- Added a second coverage pass for storage memories, items, contexts, validation, and dashboard services, raising overall coverage to 73%.
- Added question status filtering plus `taskledger question answers` with markdown and JSON output.
- Added `taskledger plan lint`, stricter executable-plan linting, and approval gating for lint failures.
- Added focused worker contexts and durable handoff snapshots for implementer and reviewer workflows.
- Added richer `next-action` output with next item, command hints, and progress details.
- Added project-root config discovery and external storage roots via `taskledger.toml`.
- Added the localhost-only read-only `taskledger serve` dashboard.
- Added an explicit failed-validation recovery path with `taskledger implement restart`.
- Added compact single-agent workflow guidance and richer `todo next` and `todo show` hints.

### Changed

- Hardened agent guardrails by requiring reasons for approval escape hatches, blocking empty-todo approvals by default, and adding durable `plan command` execution.
- Finished agent-protocol hardening with stronger typed normalization, safer plan todo materialization, and automatic todo source inference from the active lock.
- Removed redundant derived task, plan-version, and latest-run indexes so Markdown bundles remain canonical and JSON indexes remain rebuildable caches.
- Completed the broader pre-release cleanup pass from `todo.md`, including public API export cleanup, stricter storage diagnostics, canonical module paths, normalized JSON command naming, and packaging cleanup.
- Extended the serve dashboard with a dedicated read model, recent-event tail loading, route caching, and non-overlapping partial refreshes for better hot-path performance.
- Redesigned the serve dashboard into a more human-focused layout with richer sidebar metadata, accessibility coverage, and updated docs.
- Improved dashboard review ergonomics and refresh stability with pause and resume controls, diffed rerenders, preserved details state, and lazy raw-payload rendering.
- Finished release-readiness cleanup by consolidating maintained docs under RST and keeping `skills/taskledger/SKILL.md` as the single canonical skill file.

### Fixed

- Fixed `taskledger view` so todo counts and item lists reflect persisted todos instead of always showing `0/0`.
- Fixed orphan slug-directory creation under `.taskledger/tasks/` and added repair support for existing bad directories.
- Fixed repo-wide pre-commit and mypy failures across more than twenty files.
- Fixed serve response handling so client disconnects no longer produce `BrokenPipeError` tracebacks.
- Fixed the serve dashboard todo-renderer JavaScript regression that broke refresh parsing.

### Quality

- Improved testing depth across storage, dashboard, lifecycle, and documentation surfaces to support release readiness and regression protection.
