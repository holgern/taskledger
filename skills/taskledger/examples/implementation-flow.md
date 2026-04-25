# Implementation flow

1. `taskledger --root /workspace context --for implementation --format markdown`
2. `taskledger --root /workspace implement start`
3. `taskledger --root /workspace implement checklist`
4. Make the code changes for the next mandatory todo.
5. `taskledger --root /workspace implement log --message "Started wiring the new storage model."`
6. `taskledger --root /workspace implement change --path taskledger/storage/v2.py --kind edit --summary "Normalized v2 markdown storage."`
7. `taskledger --root /workspace todo done todo-0001 --evidence "uv run pytest -q" --artifact tests/test_storage.py`
8. `taskledger --root /workspace implement finish --summary "Implemented the approved plan."`
