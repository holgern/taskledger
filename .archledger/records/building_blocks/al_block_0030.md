---
schema_version: 2
id: al_block_0030
type: black_box
title: "CLI Layer"
status: proposed
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

Handles command parsing via Typer, task reference resolution (`--task` option, active task default), and output rendering (human text or JSON envelope via `cli_common.py`). Registers subcommand groups: `task`, `plan`, `question`, `implement`, `validate`, `todo`, `intro`, `file`, `link`, `require`, `lock`, `handoff`, `doctor`, `repair`, `pipeline`, `release`, `sync`, `storage`, `actor`, `report`, `ledger`.

Source refs: `taskledger/cli.py`, `taskledger/cli_common.py`, `taskledger/cli_task.py`, `taskledger/cli_plan.py`, `taskledger/cli_implement.py`, `taskledger/cli_validate.py`, `taskledger/cli_misc.py`.
