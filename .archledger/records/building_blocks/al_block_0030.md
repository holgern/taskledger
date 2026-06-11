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
updated_at: "2026-06-11T21:00:00Z"
---

Handles command parsing via Typer, task reference resolution (`--task` option, active task default), and output rendering (human text or JSON envelope via `cli_common.py`). Command families include the canonical lifecycle plus `review`, `config`, task archive operations, transfer/sync, diagnostics, and the `monitor` observer.

Source refs: `taskledger/cli.py`, `taskledger/cli_common.py`, `taskledger/command_inventory.py`, and the focused `taskledger/cli_*.py` registration modules.
