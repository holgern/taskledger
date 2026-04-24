# Implementation flow

1. `taskledger --root /workspace context rewrite-v2 --for implementation --format markdown`
2. `taskledger --root /workspace implement start rewrite-v2`
3. Make the code changes.
4. `taskledger --root /workspace implement log rewrite-v2 --message "Started wiring the new storage model."`
5. `taskledger --root /workspace implement change rewrite-v2 --path taskledger/storage/v2.py --kind edit --summary "Normalized v2 markdown storage."`
6. `taskledger --root /workspace implement finish rewrite-v2 --summary "Implemented the approved plan."`
