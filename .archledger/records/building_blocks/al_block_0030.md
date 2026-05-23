---
schema_version: 2
id: al_block_0030
type: black_box
title: "CLI Layer"
status: accepted
section: building_block_view
level: 1
parent: al_block_0029
order: 10
date: "2026-05-23"
interfaces: []
location: []
fulfilled_requirements: []
risks: []
tags: []
body_format: markdown
created_at: "2026-05-23T12:30:23Z"
updated_at: "2026-05-23T12:30:23Z"
---

Handles command parsing via Typer, task reference resolution (`--task` option, active task default), and output rendering (human text or JSON envelope via `cli_common.py`). Registers 40 command groups from `COMMAND_METADATA`: `actor`, `can`, `commands`, `context`, `deps`, `doctor`, `export`, `file`, `grep`, `handoff`, `harness`, `implement`, `import`, `init`, `intro`, `ledger`, `link`, `lock`, `migrate`, `next-action`, `pipeline`, `plan`, `question`, `reindex`, `release`, `repair`, `report`, `require`, `search`, `serve`, `snapshot`, `status`, `storage`, `sync`, `symbols`, `task`, `todo`, `tree`, `validate`, `view`.

Source refs: `taskledger/cli.py`, `taskledger/cli_common.py`, `taskledger/cli_task.py`, `taskledger/cli_plan.py`, `taskledger/cli_implement.py`, `taskledger/cli_validate.py`, `taskledger/cli_misc.py`.
