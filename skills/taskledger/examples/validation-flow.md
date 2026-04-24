# Validation flow

1. `taskledger --root /workspace handoff validation-context rewrite-v2 --format markdown`
2. `taskledger --root /workspace validate start rewrite-v2`
3. Run the validation checks.
4. `taskledger --root /workspace validate add-check rewrite-v2 --name "pytest -q" --status pass --details "Focused suite passed"`
5. `taskledger --root /workspace validate finish rewrite-v2 --result passed --summary "Validated the rewrite."`
