# Validation flow

1. `taskledger --root /workspace context --for validation --format markdown`
2. `taskledger --root /workspace validate start`
3. `taskledger --root /workspace validate status`
4. Run the validation checks.
5. `taskledger --root /workspace validate check --criterion ac-0001 --status pass --evidence "pytest -q"`
6. `taskledger --root /workspace validate finish --result passed --summary "Validated the rewrite."`
