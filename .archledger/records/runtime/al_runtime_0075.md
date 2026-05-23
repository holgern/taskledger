---
schema_version: 2
id: al_runtime_0075
type: runtime_scenario
title: "Git sync workflow for shared state"
status: accepted
section: runtime_view
order: 60
date: "2026-05-23"
participants: []
trigger: "Developer runs taskledger sync git init to set up an external sync repo"
result: ""
body_format: markdown
created_at: "2026-05-23T19:30:00Z"
updated_at: "2026-05-23T19:30:00Z"
---

**Trigger**: Developer runs `taskledger sync git init` to set up an external sync repo.

**Flow**:

1. `sync git init` → Moves or copies `.taskledger/` content into a dedicated Git repository, updates `taskledger.toml` with `external_dir`
2. `sync preflight` → Checks that no active locks would conflict with a sync operation
3. `sync git commit --message "..."` → Commits current state to the sync repo
4. `sync git export-local` / `sync git import-local` → Exchanges state between the sync repo and the project
5. `sync git status` → Shows working tree status of the sync repo
6. `sync git paths` → Shows resolved paths for the sync repo and project
7. `cd "$(taskledger sync git cd)"` → Opens a shell in the sync repo directory for manual Git operations

**Result**: Taskledger state is stored in a separate Git repository that can be versioned and shared manually. The design intentionally avoids automated push/pull to prevent merge conflicts — users run `git push`/`git pull` directly in the sync repo.

**Key source**: `taskledger/services/git_sync.py`, `taskledger/cli_sync.py`, `taskledger/api/sync.py`.
