# Implementation flow

1. `taskledger --root /workspace context --for implementation --format markdown`
2. `taskledger --root /workspace implement start`
3. Make the code changes.
4. `taskledger --root /workspace implement log --message "Started wiring the new storage model."`
5. `taskledger --root /workspace implement change --path taskledger/storage/v2.py --kind edit --summary "Normalized v2 markdown storage."`
6. `taskledger --root /workspace implement finish --summary "Implemented the approved plan."`
