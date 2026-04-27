# Implementation flow

1. `taskledger --root /workspace next-action`
2. Inspect the `next_item` and `next_command` output before opening broader context.
3. `taskledger --root /workspace context --for implementation --format markdown`
4. `taskledger --root /workspace implement start`
5. `taskledger --root /workspace implement checklist`
6. Make the code changes for the next mandatory todo.
7. `taskledger --root /workspace implement log --message "Started wiring the new storage model."`
8. `taskledger --root /workspace implement change --path taskledger/storage/v2.py --kind edit --summary "Normalized v2 markdown storage."`
9. `taskledger --root /workspace todo done todo-0001 --evidence "uv run pytest -q" --artifact tests/test_storage.py`
10. `taskledger --root /workspace implement finish --summary "Implemented the approved plan."`

Example `next-action` output:

```text
todo-work: Implementation is in progress; 1 todos remain.
Next todo: todo-0001 -- Normalize the storage model.
Command: taskledger todo show todo-0001
Mark todo done after evidence exists: taskledger todo done todo-0001 --evidence "..."
Progress: 0/1 todos done
```
