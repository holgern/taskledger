# Validation flow

1. `taskledger --root /workspace next-action`
2. Inspect the `next_item`, `commands`, and `progress` output before broader context.
3. `taskledger --root /workspace context --for validation --format markdown`
4. `taskledger --root /workspace validate start`
5. `taskledger --root /workspace validate status`
6. Run the validation checks.
7. `taskledger --root /workspace validate check --criterion ac-0001 --status pass --evidence "pytest -q"`
8. `taskledger --root /workspace validate finish --result passed --summary "Validated the rewrite."`

Example `next-action` output:

```text
validate-check: Validation is in progress; required checks remain.
Next criterion: ac-0001 -- Mandatory behavior is checked.
Command: taskledger validate check --criterion ac-0001 --status pass --evidence "..."
Show validation status: taskledger validate status
Validation progress: 0/1 satisfied
```
