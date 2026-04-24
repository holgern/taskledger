# Validation flow

1. `taskledger --root /workspace context rewrite-v2 --for validation --format markdown`
2. `taskledger --root /workspace validate start rewrite-v2`
3. Run the validation checks.
4. `taskledger --root /workspace validate check rewrite-v2 --criterion ac-0001 --status pass --evidence "pytest -q"`
5. `taskledger --root /workspace validate finish rewrite-v2 --result passed --summary "Validated the rewrite."`
