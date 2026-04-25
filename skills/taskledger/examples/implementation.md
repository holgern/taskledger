# Implementation example

Implement an approved task:

```bash
taskledger context --for implementation --format markdown
taskledger implement start
taskledger implement checklist
taskledger implement log --message "Reworked parser entrypoint."
taskledger implement change --path taskledger/parser.py --kind edit --summary "Normalized parser fallback behavior."
taskledger todo done todo-0001 --evidence "pytest -q tests/test_parser.py" --artifact tests/test_parser.py
taskledger implement finish --summary "Implemented the approved parser changes."
```
